import 'package:flutter/material.dart';
import 'package:frontend/features/live2d/live2d_widget.dart';

/// Live2D 캐릭터의 모션 및 감정을 제어하는 버튼 그룹 위젯
class Live2DMotionButtons extends StatelessWidget {
  final GlobalKey<Live2DWidgetState> live2dKey;

  const Live2DMotionButtons({super.key, required this.live2dKey});

  @override
  Widget build(BuildContext context) {
    return Positioned(
      right: 16,
      top: 100,
      bottom: 100, // 화면 위아래 여백 확보
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // [신규] 감정별 모션 제어 버튼 그룹
          _buildEmotionGroup(),
          const SizedBox(width: 8),
          // 기존 모션 제어 버튼 그룹
          _buildMotionGroup(),
        ],
      ),
    );
  }

  /// 감정별 모션 제어 버튼 그룹 빌드
  Widget _buildEmotionGroup() {
    final emotions = [
      {'index': 2, 'icon': Icons.face, 'label': '기본'},
      {'index': 21, 'icon': Icons.auto_awesome, 'label': '반짝'},
      {'index': 4, 'icon': Icons.sentiment_very_dissatisfied, 'label': '삐짐'},
      {'index': 18, 'icon': Icons.favorite, 'label': '애정'},
      {'index': 23, 'icon': Icons.wb_sunny, 'label': '따뜻'},
    ];

    return SizedBox(
      width: 60,
      child: SingleChildScrollView(
        child: Column(
          children: emotions.map((emo) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 8.0),
              child: _buildControlButton(
                emo['icon'] as IconData,
                emo['label'] as String,
                () => live2dKey.currentState?.playMotion('', emo['index'] as int),
                color: Colors.purpleAccent.withAlpha(150),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  /// 모션 제어 버튼 그룹 빌드
  Widget _buildMotionGroup() {
    return SizedBox(
      width: 60,
      child: SingleChildScrollView(
        child: Column(
          children: List.generate(28, (index) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 8.0),
              child: _buildControlButton(
                index == 0 ? Icons.accessibility_new : (index == 27 ? Icons.hearing : Icons.play_arrow),
                'M$index',
                () => live2dKey.currentState?.playMotion('', index),
                color: index == 0 ? Colors.blueAccent.withAlpha(150) : (index == 27 ? Colors.orangeAccent.withAlpha(150) : null),
              ),
            );
          }),
        ),
      ),
    );
  }

  /// 개별 제어 버튼 생성 (공통)
  Widget _buildControlButton(
    IconData icon,
    String label,
    VoidCallback onPressed, {
    Color? color,
  }) {
    return SizedBox(
      width: 60,
      height: 60,
      child: FloatingActionButton(
        heroTag: null, // 여러 개의 FAB가 있을 때 충돌 방지
        mini: true,
        backgroundColor: color ?? Colors.white.withAlpha(50),
        onPressed: onPressed,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 18, color: Colors.white),
            Text(
              label,
              style: const TextStyle(fontSize: 10, color: Colors.white),
            ),
          ],
        ),
      ),
    );
  }
}
