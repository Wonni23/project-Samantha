import 'dart:async';
import 'dart:typed_data';

import 'package:equatable/equatable.dart';
import 'package:flutter_sound/flutter_sound.dart';
import 'package:frontend/core/utils/logger.dart';
import 'package:frontend/core/utils/platform_utils.dart';
import 'package:frontend/features/home/providers/ai_response_provider.dart';
import 'package:frontend/features/home/providers/sound_player_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'audio_recorder_provider.g.dart';

@Riverpod(keepAlive: true)
class AudioRecorderNotifier extends _$AudioRecorderNotifier {
  FlutterSoundRecorder? _recorder;

  @override
  AudioRecorderState build() {
    _recorder = FlutterSoundRecorder();
    _init();

    // Dispose logic
    ref.onDispose(() {
      _recorder?.closeRecorder();
      _recorder = null;
    });

    return const AudioRecorderState();
  }

  Future<void> _init() async {
    await _recorder!.openRecorder();
  }

  /// 녹음을 시작합니다.
  Future<void> startRecording() async {
    // [보안] AI 응답 중이거나 재생 중일 때 녹음 방지
    final aiState = ref.read(aIResponseProvider);
    final player = ref.read(soundPlayerProvider);
    
    if (aiState.isReceiving || aiState.isAudioPlaying || player.isPlaying) {
      logger.w('Cannot start recording while Samantha is responding or playing audio.');
      return;
    }

    try {
      final status = await Permission.microphone.request();
      if (status != PermissionStatus.granted) {
        throw RecordingPermissionException('Microphone permission not granted');
      }

      state = const AudioRecorderState(isRecording: true);

      // 웹에서 Blob 생성을 안정화하기 위해 가상 경로를 지정합니다.
      const recordingPath = 'audio.webm';
      await _recorder!.startRecorder(
        toFile: recordingPath,
        codec: Codec.opusWebM, // 웹 호환성을 위한 코덱
      );
    } catch (e) {
      logger.e('!!! START RECORDER FAILED', error: e);
      _resetRecording();
    }
  }

  /// 녹음을 중지하고 결과물 경로(URL)를 저장합니다.
  Future<void> stopRecording() async {
    try {
      // `stopRecorder`는 파일 경로(모바일) 또는 Blob URL(웹)을 반환합니다.
      final path = await _recorder!.stopRecorder();
      state = state.copyWith(
        isRecording: false,
        recordingFinished: true,
        audioPath: path,
      );
    } catch (e) {
      logger.e('!!! STOP RECORDER FAILED', error: e);
      _resetRecording();
    }
  }

  /// 녹음된 오디오를 재생합니다.
  Future<void> startPlaying() async {
    final path = state.audioPath;
    if (path == null) return;

    final player = ref.read(soundPlayerProvider);

    try {
      // 플레이어가 닫혀 있다면 다시 엽니다.
      if (!player.isOpen()) {
        await player.openPlayer();
      }

      await player.startPlayer(
        fromURI: path,
        codec: Codec.opusWebM,
        whenFinished: () {
          state = state.copyWith(isPlaying: false);
        },
      );
      state = state.copyWith(isPlaying: true);
    } catch (e) {
      logger.e('!!! START PLAYER FAILED', error: e);
      state = state.copyWith(isPlaying: false);
    }
  }

  Future<void> stopPlaying() async {
    final player = ref.read(soundPlayerProvider);
    try {
      await player.stopPlayer();
      state = state.copyWith(isPlaying: false);
    } catch (e) {
      logger.e('!!! STOP PLAYER FAILED', error: e);
    }
  }

  /// [수정] 녹음된 오디오를 바이트 데이터로 반환합니다.
  Future<Uint8List?> getRecordedAudioBytes() async {
    final path = state.audioPath;
    if (path == null) return null;

    try {
      return await PlatformUtilsImpl.fetchBytes(path);
    } catch (e) {
      logger.e('!!! GET AUDIO BYTES FAILED', error: e);
      return null;
    }
  }

  /// 현재 녹음 상태를 초기화합니다. (오래된 녹음 파일을 지우는 효과)
  void clearRecording() {
    state = const AudioRecorderState();
  }

  void _resetRecording() {
    state = const AudioRecorderState();
  }
}

/// 오디오 녹음/재생 관련 상태를 관리하는 클래스
class AudioRecorderState extends Equatable {
  final bool isRecording;
  final bool isPlaying;
  final bool recordingFinished;
  final String? audioPath; // 녹음 파일의 경로 또는 URL

  const AudioRecorderState({
    this.isRecording = false,
    this.isPlaying = false,
    this.recordingFinished = false,
    this.audioPath,
  });

  AudioRecorderState copyWith({
    bool? isRecording,
    bool? isPlaying,
    bool? recordingFinished,
    String? audioPath,
  }) {
    return AudioRecorderState(
      isRecording: isRecording ?? this.isRecording,
      isPlaying: isPlaying ?? this.isPlaying,
      recordingFinished: recordingFinished ?? this.recordingFinished,
      audioPath: audioPath ?? this.audioPath,
    );
  }

  @override
  List<Object?> get props => [
    isRecording,
    isPlaying,
    recordingFinished,
    audioPath,
  ];
}

class RecordingPermissionException implements Exception {
  final String message;
  RecordingPermissionException(this.message);
}
