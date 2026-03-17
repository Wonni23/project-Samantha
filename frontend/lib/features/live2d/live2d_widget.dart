import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'live2d_controller.dart';

/// Live2D 모델을 표시하는 Flutter Widget (웹/모바일 통합 지원)
class Live2DWidget extends ConsumerStatefulWidget {
  final String modelPath;
  final double? width;
  final double? height;

  const Live2DWidget({
    super.key,
    required this.modelPath,
    this.width,
    this.height,
  });

  @override
  ConsumerState<Live2DWidget> createState() => Live2DWidgetState();
}

class Live2DWidgetState extends ConsumerState<Live2DWidget> {
  late Live2DController _controller;

  @override
  void initState() {
    super.initState();
    final viewId = 'live2d-view-${DateTime.now().millisecondsSinceEpoch}';
    final canvasId = 'live2d-canvas';

    // 이제 플랫폼별 구현체가 팩토리 메서드에 의해 안전하게 생성됩니다.
    _controller = Live2DController(viewId, canvasId, widget.modelPath);
  }

  /// 모션 재생
  void playMotion(String group, [int index = 0]) => _controller.playMotion(group, index);

  /// 입 모양 조절 (0.0 ~ 1.0)
  void setMouthOpen(double value) => _controller.setMouthOpen(value);

  /// 파라미터 값 직접 설정
  void setParameterValue(String id, double value) => _controller.setParameterValue(id, value);

  /// [신규] 립싱크 시작
  void startLipSync() => _controller.startLipSync();

  /// [신규] 립싱크 중지
  void stopLipSync() => _controller.stopLipSync();

  /// [신규] 귀 기울이는 자세 시작
  void startListeningPose() => _controller.startListeningPose();

  /// [신규] 커스텀 자세 해제
  void stopListeningPose() => _controller.stopListeningPose();

  /// [신규] 실시간 진폭 값 가져오기
  double getLipSyncValue() => _controller.getLipSyncValue();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: widget.width ?? double.infinity,
      height: widget.height ?? 400,
      child: _controller.buildView(),
    );
  }
}
