import 'dart:async';
import 'dart:typed_data';

import 'package:equatable/equatable.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_sound/flutter_sound.dart';
import 'package:frontend/core/network/socket_service.dart';
import 'package:frontend/core/utils/logger.dart';
import 'package:frontend/core/utils/platform_utils.dart';
import 'package:frontend/features/chat/data/models/chat_message.dart';
import 'package:frontend/features/chat/providers/chat_provider.dart';
import 'package:frontend/features/home/providers/sound_player_provider.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'ai_response_provider.g.dart';

// --- State Class ---
class AIResponseState extends Equatable {
  final String? audioPath;
  final bool isReceiving;
  final bool isAudioPlaying;
  final String? emotion;
  final String? error;

  const AIResponseState({
    this.audioPath,
    this.isReceiving = false,
    this.isAudioPlaying = false,
    this.emotion,
    this.error,
  });

  AIResponseState copyWith({
    String? audioPath,
    bool? isReceiving,
    bool? isAudioPlaying,
    String? emotion,
    String? error,
    bool clearAudioPath = false,
  }) {
    return AIResponseState(
      audioPath: clearAudioPath ? null : audioPath ?? this.audioPath,
      isReceiving: isReceiving ?? this.isReceiving,
      isAudioPlaying: isAudioPlaying ?? this.isAudioPlaying,
      emotion: emotion ?? this.emotion,
      error: error ?? this.error,
    );
  }

  @override
  List<Object?> get props => [
    audioPath,
    isReceiving,
    isAudioPlaying,
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

  /// 음성 데이터 전송 (HTTP) 및 응답 처리
  Future<void> getAIResponse(Uint8List audioData) async {
    state = const AIResponseState(isReceiving: true);
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

    state = const AIResponseState(isReceiving: true);
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
    final bool useDedicatedWebPlayer = kIsWeb;
    final player = useDedicatedWebPlayer
        ? FlutterSoundPlayer()
        : ref.read(soundPlayerProvider);
    final playbackDone = Completer<void>();
    Timer? playbackCompletionPoller;
    bool hasStartedPlayback = false;

    void completePlayback() {
      if (!playbackDone.isCompleted) {
        playbackDone.complete();
      }
    }

    try {
      if (!player.isOpen()) {
        await player.openPlayer();
      }
      if (ref.mounted) {
        state = state.copyWith(isAudioPlaying: true);
      }
      await player.startPlayer(
        fromURI: path,
        codec: Codec.mp3,
        whenFinished: () {
          completePlayback();
        },
      );

      playbackCompletionPoller = Timer.periodic(
        const Duration(milliseconds: 150),
        (_) {
          if (player.isPlaying) {
            hasStartedPlayback = true;
            return;
          }

          if (hasStartedPlayback) {
            completePlayback();
          }
        },
      );

      await playbackDone.future.timeout(
        const Duration(seconds: 90),
        onTimeout: () {
          logger.w(
            'Playback completion timeout. Continue queue without waiting more.',
          );
          completePlayback();
        },
      );
    } catch (e) {
      completePlayback();
      logger.e('Audio Playback Error', error: e);
    } finally {
      if (ref.mounted) {
        state = state.copyWith(isAudioPlaying: false);
      }
      playbackCompletionPoller?.cancel();
      if (useDedicatedWebPlayer) {
        try {
          if (player.isPlaying) {
            await player.stopPlayer();
          }
        } catch (e) {
          logger.w('Failed to stop dedicated web player: $e');
        }
        await player.closePlayer();
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
