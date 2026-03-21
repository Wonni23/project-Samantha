import 'dart:async';
import 'dart:typed_data';
import 'dart:convert'; // base64Encode를 위해 상단으로 이동

import 'package:equatable/equatable.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_sound/flutter_sound.dart';
import 'package:frontend/core/network/socket_service.dart';
import 'package:frontend/core/utils/logger.dart';
import 'package:frontend/core/utils/platform_utils.dart';
import 'package:frontend/features/chat/data/models/chat_message.dart';
import 'package:frontend/features/chat/providers/chat_provider.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'ai_response_provider.g.dart';

// --- State Class ---
class AIResponseState extends Equatable {
  final String? audioPath;
  final String? audioBase64; // [신규] WebView 재생용 Base64 데이터
  final bool isReceiving;
  final bool isAudioPlaying;
  final bool isProcessing; // [신규] 전체 프로세스(텍스트+오디오) 진행 여부
  final String? emotion;
  final String? error;

  const AIResponseState({
    this.audioPath,
    this.audioBase64,
    this.isReceiving = false,
    this.isAudioPlaying = false,
    this.isProcessing = false,
    this.emotion,
    this.error,
  });

  AIResponseState copyWith({
    String? audioPath,
    String? audioBase64,
    bool? isReceiving,
    bool? isAudioPlaying,
    bool? isProcessing,
    String? emotion,
    String? error,
    bool clearAudioPath = false,
    bool clearAudioBase64 = false,
  }) {
    return AIResponseState(
      audioPath: clearAudioPath ? null : audioPath ?? this.audioPath,
      audioBase64: clearAudioBase64 ? null : audioBase64 ?? this.audioBase64,
      isReceiving: isReceiving ?? this.isReceiving,
      isAudioPlaying: isAudioPlaying ?? this.isAudioPlaying,
      isProcessing: isProcessing ?? this.isProcessing,
      emotion: emotion ?? this.emotion,
      error: error ?? this.error,
    );
  }

  @override
  List<Object?> get props => [
    audioPath,
    audioBase64,
    isReceiving,
    isAudioPlaying,
    isProcessing,
    emotion,
    error,
  ];
}

// --- Notifier Provider ---
@Riverpod(keepAlive: true)
class AIResponseNotifier extends _$AIResponseNotifier {
  StreamSubscription? _sttSubscription;
  StreamSubscription? _textChunkSubscription;
  StreamSubscription? _doneSubscription;
  StreamSubscription<String>? _emotionSubscription;
  StreamSubscription<int>? _textSegmentStartSubscription;
  StreamSubscription<Uint8List>? _textAudioChunkSubscription;
  StreamSubscription<int>? _textSegmentEndSubscription;
  StreamSubscription<String>? _textAudioErrorSubscription;

  final Map<int, BytesBuilder> _textSegmentBuffers = <int, BytesBuilder>{};
  final List<Uint8List> _textPlaybackQueue = <Uint8List>[];
  final List<Uint8List> _legacyTextAudioChunks = <Uint8List>[];
  int? _activeTextSegmentIndex;
  bool _isTextAudioSessionActive = false;
  bool _isQueuePlaying = false;
  Completer<void>? _queueDrainCompleter;
  Completer<void>? _playbackCompleter; // [신규] WebView 오디오 재생 완료 대기용

  @override
  AIResponseState build() {
    final socketService = ref.watch(socketServiceProvider);

    // [중요] 소켓 이벤트를 통한 채팅 업데이트 로직 복구
    _sttSubscription?.cancel();
    _sttSubscription = socketService.onSttText.listen((text) {
      final chat = ref.read(chatProvider.notifier);
      chat.addUserMessage(text);
      chat.addMessage(ChatMessage(message: '...', isUser: false));
    });

    _textChunkSubscription?.cancel();
    _textChunkSubscription = socketService.onTextChunk.listen((chunk) {
      ref.read(chatProvider.notifier).updateLastBotMessage(chunk);
    });

    _emotionSubscription?.cancel();
    _emotionSubscription = socketService.onEmotion.listen((emotion) {
      state = state.copyWith(emotion: emotion);
    });

    _doneSubscription?.cancel();
    _doneSubscription = socketService.onResponseDone.listen((_) async {
      if (state.isReceiving) {
        state = state.copyWith(isReceiving: false);
      }
      await _finishTextAudioSession();
    });

    ref.onDispose(() {
      _sttSubscription?.cancel();
      _textChunkSubscription?.cancel();
      _emotionSubscription?.cancel();
      _doneSubscription?.cancel();
      _cancelTextAudioSubscriptions();
    });

    return const AIResponseState();
  }

  void _cancelTextAudioSubscriptions() {
    _textSegmentStartSubscription?.cancel();
    _textSegmentStartSubscription = null;

    _textAudioChunkSubscription?.cancel();
    _textAudioChunkSubscription = null;

    _textSegmentEndSubscription?.cancel();
    _textSegmentEndSubscription = null;

    _textAudioErrorSubscription?.cancel();
    _textAudioErrorSubscription = null;
  }

  void _resetTextAudioSessionState() {
    _activeTextSegmentIndex = null;
    _isTextAudioSessionActive = false;
    _textSegmentBuffers.clear();
    _textPlaybackQueue.clear();
    _legacyTextAudioChunks.clear();
  }

  void _startTextAudioSession() {
    _cancelTextAudioSubscriptions();
    _resetTextAudioSessionState();
    _isTextAudioSessionActive = true;

    final socketService = ref.read(socketServiceProvider);

    _textSegmentStartSubscription = socketService.onAudioSegmentStart.listen((
      segmentIndex,
    ) {
      if (!_isTextAudioSessionActive) return;
      _activeTextSegmentIndex = segmentIndex;
      _textSegmentBuffers.putIfAbsent(segmentIndex, BytesBuilder.new);
    });

    _textAudioChunkSubscription = socketService.onAudioChunk.listen((chunk) {
      if (!_isTextAudioSessionActive) return;

      final segmentIndex = _activeTextSegmentIndex;
      if (segmentIndex == null) {
        _legacyTextAudioChunks.add(chunk);
        return;
      }

      final buffer = _textSegmentBuffers.putIfAbsent(
        segmentIndex,
        BytesBuilder.new,
      );
      buffer.add(chunk);
    });

    _textSegmentEndSubscription = socketService.onAudioSegmentEnd.listen((
      segmentIndex,
    ) {
      if (!_isTextAudioSessionActive) return;

      final buffer = _textSegmentBuffers.remove(segmentIndex);
      if (buffer == null) return;

      final segmentAudio = buffer.toBytes();
      if (segmentAudio.isEmpty) return;

      _textPlaybackQueue.add(segmentAudio);
      if (_activeTextSegmentIndex == segmentIndex) {
        _activeTextSegmentIndex = null;
      }
      unawaited(_drainTextPlaybackQueue());
    });

    _textAudioErrorSubscription = socketService.onErrorOccurred.listen((
      errorMsg,
    ) {
      _cancelTextAudioSubscriptions();
      _resetTextAudioSessionState();
      if (ref.mounted) {
        state = state.copyWith(
          isReceiving: false,
          isAudioPlaying: false,
          isProcessing: false, // [신규] 에러 시 종료
          error: errorMsg,
        );
      }
    });
  }

  Future<void> _finishTextAudioSession() async {
    if (!_isTextAudioSessionActive) return;
    _isTextAudioSessionActive = false;

    final remainingSegmentIndexes = _textSegmentBuffers.keys.toList()..sort();
    for (final segmentIndex in remainingSegmentIndexes) {
      final buffer = _textSegmentBuffers.remove(segmentIndex);
      if (buffer == null) continue;
      final segmentAudio = buffer.toBytes();
      if (segmentAudio.isNotEmpty) {
        _textPlaybackQueue.add(segmentAudio);
      }
    }

    if (_textPlaybackQueue.isEmpty && _legacyTextAudioChunks.isNotEmpty) {
      _textPlaybackQueue.add(_combineChunks(_legacyTextAudioChunks));
    }

    _cancelTextAudioSubscriptions();
    await _drainTextPlaybackQueue();
    _resetTextAudioSessionState();

    // [신규] 모든 큐 처리가 완료된 후 processing 종료
    if (ref.mounted) {
      state = state.copyWith(isProcessing: false);
    }
  }

  Future<void> _drainTextPlaybackQueue() async {
    if (_isQueuePlaying) {
      await _queueDrainCompleter?.future;
      return;
    }
    _isQueuePlaying = true;
    _queueDrainCompleter = Completer<void>();

    try {
      while (_textPlaybackQueue.isNotEmpty) {
        final segmentAudio = _textPlaybackQueue.removeAt(0);
        if (segmentAudio.isEmpty) continue;

        final playablePath = await PlatformUtilsImpl.getPlayableUrl(
          segmentAudio,
        );
        if (!ref.mounted) return;

        state = state.copyWith(audioPath: playablePath);
        await _playAudio(playablePath);
      }
    } finally {
      _isQueuePlaying = false;
      final drainCompleter = _queueDrainCompleter;
      if (drainCompleter != null && !drainCompleter.isCompleted) {
        drainCompleter.complete();
      }
      _queueDrainCompleter = null;
    }
  }

  /// 외부(HomePage)에서 오디오 재생 완료를 알림
  void notifyPlaybackFinished() {
    if (_playbackCompleter != null && !_playbackCompleter!.isCompleted) {
      _playbackCompleter!.complete();
    }
  }

  /// 음성 데이터 전송 (HTTP) 및 응답 처리
  Future<void> getAIResponse(Uint8List audioData) async {
    state = const AIResponseState(isReceiving: true, isProcessing: true);
    _startTextAudioSession();

    // 소켓으로 음성 blob 전송
    ref.read(socketServiceProvider).sendAudio(audioData);
  }

  /// 텍스트 메시지 전송 (소켓)
  void sendTextMessage(String message) {
    if (message.trim().isEmpty) return;

    final chat = ref.read(chatProvider.notifier);
    chat.addUserMessage(message);
    chat.addMessage(ChatMessage(message: '...', isUser: false));

    state = const AIResponseState(isReceiving: true, isProcessing: true);
    _startTextAudioSession();

    // 소켓으로 텍스트 전송
    ref.read(socketServiceProvider).sendTextMessage(message);
  }

  Uint8List _combineChunks(List<Uint8List> chunks) {
    final bytes = BytesBuilder();
    for (var chunk in chunks) {
      bytes.add(chunk);
    }
    return bytes.toBytes();
  }

  Future<void> _playAudio(String path) async {
    final bool isMobile = !kIsWeb;
    
    try {
      // 1. 오디오 바이트 로드
      final audioBytes = await PlatformUtilsImpl.fetchBytes(path);
      if (audioBytes == null) return;

      if (isMobile) {
        // [모바일 핵심] 네이티브 플레이어 대신 WebView로 오디오 데이터 전송
        final base64Audio = base64Encode(audioBytes);
        
        // 새 재생 세션을 위한 Completer 초기화
        _playbackCompleter = Completer<void>();

        if (ref.mounted) {
          // audioBase64 필드를 업데이트하여 HomePage 리스너가 감지하게 함
          state = state.copyWith(
            isAudioPlaying: true, 
            audioBase64: base64Audio,
          );
        }
        
        // [수정] 하드코딩된 5초 대기 대신 WebView에서 오는 완료 신호를 대기
        await _playbackCompleter!.future.timeout(
          const Duration(seconds: 20),
          onTimeout: () => logger.w('[Audio] Playback timeout in WebView'),
        );
      } else {
        // [웹] 기존 로직 유지 (웹은 이미 브라우저 오디오 분석 작동 중)
        final player = FlutterSoundPlayer();
        await player.openPlayer();
        await player.startPlayer(
          fromURI: path,
          codec: Codec.mp3,
          whenFinished: () async {
            await player.closePlayer();
          },
        );
        // 재생 중 대기
        while (player.isPlaying) {
          await Future.delayed(const Duration(milliseconds: 200));
        }
      }
    } catch (e) {
      logger.e('Audio Playback Error', error: e);
    } finally {
      if (ref.mounted) {
        state = state.copyWith(
          isAudioPlaying: false, 
          clearAudioBase64: true,
        );
      }
      PlatformUtilsImpl.revokeUrl(path);
    }
  }

  void clearAIResponse() {
    state = const AIResponseState();
    _cancelTextAudioSubscriptions();
    _resetTextAudioSessionState();
  }
}
