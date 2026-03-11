import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/network/socket_service.dart';
import 'package:frontend/features/home/providers/ai_response_provider.dart';
import 'package:frontend/features/home/providers/audio_recorder_provider.dart';

/// 어스 앤 샌드 테마 컬러 상수
class AppColors {
  static const Color base = Color(0xFFEFEBE0);       // 코지 오트밀
  static const Color primary = Color(0xFF6D4C41);    // 딥 브론즈
  static const Color text = Color(0xFF3E2723);       // 차콜 브라운
  static const Color accentSage = Color(0xFF8E9775); // 뮤트 세이지
  static const Color accentBrown = Color(0xFF8D8171); // 뮤트 브라운
}

/// 음성 모드에서 사용되는 통합 음성 컨트롤 위젯
class VoiceModeControls extends ConsumerWidget {
  const VoiceModeControls({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final audioState = ref.watch(audioRecorderProvider);
    final audioNotifier = ref.read(audioRecorderProvider.notifier);
    final aiState = ref.watch(aIResponseProvider);
    final aiNotifier = ref.read(aIResponseProvider.notifier);
    final socketStatus = ref.watch(socketStatusProvider);

    // AI 응답 중이거나 오디오 재생 중일 때의 상태
    final bool isBusy = aiState.isReceiving || aiState.isAudioPlaying || audioState.isPlaying;

    /// 음성 메시지 처리 로직 (녹음 시작 또는 중지 후 즉시 전송)
    Future<void> handleVoiceInteraction() async {
      if (audioState.isRecording) {
        // 1. 녹음 중지
        await audioNotifier.stopRecording();

        // 2. 녹음된 데이터 전송
        final bytes = await audioNotifier.getRecordedAudioBytes();
        if (bytes != null && socketStatus == SocketStatus.connected) {
          await aiNotifier.getAIResponse(bytes);
        }

        // 3. 상태 초기화
        audioNotifier.clearRecording();
      } else {
        // AI가 응답 중이거나 다른 오디오가 재생 중이면 시작 불가
        if (isBusy) return;

        // 녹음 시작
        aiNotifier.clearAIResponse();
        await audioNotifier.startRecording();
      }
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // 상태 표시 텍스트
        Padding(
          padding: const EdgeInsets.only(bottom: 24),
          child: Text(
            audioState.isRecording
                ? '말씀을 끝내려면 버튼을 누르세요'
                : (isBusy ? '사만다의 응답을 듣는 중...' : '마이크를 눌러 대화를 시작하세요'),
            style: TextStyle(
              color: Colors.white.withAlpha(230),
              fontSize: 17,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.5,
              shadows: [
                Shadow(
                  color: Colors.black.withAlpha(80),
                  offset: const Offset(0, 2),
                  blurRadius: 4,
                ),
              ],
            ),
          ),
        ),
        
        // 대형 원형 음성 버튼
        GestureDetector(
          onTap: handleVoiceInteraction,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: audioState.isRecording
                  ? AppColors.accentSage
                  : (isBusy ? AppColors.accentBrown.withAlpha(120) : AppColors.primary),
              boxShadow: [
                if (audioState.isRecording)
                  BoxShadow(
                    color: AppColors.accentSage.withAlpha(100),
                    blurRadius: 25,
                    spreadRadius: 8,
                  ),
                if (!audioState.isRecording && !isBusy)
                  BoxShadow(
                    color: AppColors.primary.withAlpha(60),
                    blurRadius: 15,
                    spreadRadius: 2,
                  ),
              ],
              border: Border.all(
                color: Colors.white.withAlpha(50),
                width: 3,
              ),
            ),
            child: Icon(
              audioState.isRecording ? Icons.stop_rounded : Icons.mic_rounded,
              color: isBusy && !audioState.isRecording 
                  ? Colors.white.withAlpha(100) 
                  : Colors.white,
              size: 52,
            ),
          ),
        ),
      ],
    );
  }
}
