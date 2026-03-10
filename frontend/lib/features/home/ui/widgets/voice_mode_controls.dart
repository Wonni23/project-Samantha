import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/network/socket_service.dart';
import 'package:frontend/features/home/providers/ai_response_provider.dart';
import 'package:frontend/features/home/providers/audio_recorder_provider.dart';

/// 음성 모드에서 사용되는 오디오 녹음/재생/전송 컨트롤 위젯
class VoiceModeControls extends ConsumerWidget {
  const VoiceModeControls({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final audioState = ref.watch(audioRecorderProvider);
    final audioNotifier = ref.read(audioRecorderProvider.notifier);
    final aiState = ref.watch(aIResponseProvider);
    final aiNotifier = ref.read(aIResponseProvider.notifier);
    final socketStatus = ref.watch(socketStatusProvider);

    // AI 응답 중이거나 재생 중일 때 녹음/삭제 버튼 비활성화 여부
    final bool isBusy =
        aiState.isReceiving || aiState.isAudioPlaying || audioState.isPlaying;

    return Column(
      children: [
        // 녹음 버튼 (녹음/중지/다시녹음)
        ElevatedButton.icon(
          onPressed: audioState.isRecording
              ? audioNotifier.stopRecording
              : (isBusy
                  ? null // AI 응답 중이거나 재생 중이면 녹음 시작 불가
                  : (audioState.audioPath != null
                      ? audioNotifier.clearRecording
                      : () {
                          aiNotifier.clearAIResponse();
                          audioNotifier.startRecording();
                        })),
          icon: Icon(
            audioState.isRecording
                ? Icons.stop
                : (audioState.audioPath != null
                      ? Icons.delete_outline
                      : Icons.mic),
          ),
          label: Text(
            audioState.isRecording
                ? '녹음 중지'
                : (audioState.audioPath != null ? '다시 녹음' : '음성 녹음'),
          ),
          style: _getButtonStyle(isEnabled: !isBusy || audioState.isRecording),
        ),
        const SizedBox(height: 12),

        // 재생 버튼
        ElevatedButton.icon(
          onPressed: (audioState.isRecording || audioState.audioPath == null)
              ? null
              : (audioState.isPlaying
                    ? audioNotifier.stopPlaying
                    : audioNotifier.startPlaying),
          icon: Icon(
            audioState.isPlaying
                ? Icons.stop_circle_outlined
                : Icons.play_circle_outline,
          ),
          label: Text(audioState.isPlaying ? '재생 중지' : '녹음 재생'),
          style: _getButtonStyle(),
        ),
        const SizedBox(height: 12),

        // 전송 버튼
        ElevatedButton.icon(
          onPressed:
              (audioState.audioPath != null &&
                  !aiState.isReceiving &&
                  !aiState.isAudioPlaying &&
                  socketStatus == SocketStatus.connected)
              ? () async {
                  final bytes = await audioNotifier.getRecordedAudioBytes();
                  if (bytes != null) {
                    await aiNotifier.getAIResponse(bytes);
                  }
                  audioNotifier.clearRecording();
                }
              : null,
          icon: (aiState.isReceiving || aiState.isAudioPlaying)
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    color: Colors.white,
                    strokeWidth: 2,
                  ),
                )
              : const Icon(Icons.send),
          label: Text(
            (aiState.isReceiving || aiState.isAudioPlaying)
                ? '응답 듣는 중...'
                : '전송하기',
          ),
          style: _getSendButtonStyle(
            audioState.audioPath != null &&
                !aiState.isReceiving &&
                !aiState.isAudioPlaying &&
                socketStatus == SocketStatus.connected,
          ),
        ),
      ],
    );
  }

  /// 기본 버튼 스타일
  ButtonStyle _getButtonStyle({bool isEnabled = true}) {
    return ElevatedButton.styleFrom(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
      backgroundColor: isEnabled ? null : Colors.grey.withAlpha(100),
    );
  }

  /// 전송 버튼 스타일 (활성/비활성 상태에 따라 색상 변경)
  ButtonStyle _getSendButtonStyle(bool isEnabled) {
    return ElevatedButton.styleFrom(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
      backgroundColor: isEnabled ? Colors.blueAccent : Colors.grey,
      foregroundColor: Colors.white,
    );
  }
}
