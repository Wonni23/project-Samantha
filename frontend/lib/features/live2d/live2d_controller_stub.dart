import 'package:flutter/material.dart';
import 'live2d_controller.dart';

/// 플랫폼별 구현체가 로드되지 않았을 때 사용하는 스텁(Stub) 구현체입니다.
class Live2DControllerImpl implements Live2DController {
  @override
  VoidCallback? onPlaybackFinished;

  Live2DControllerImpl(String viewId, String canvasId, String modelPath, {this.onPlaybackFinished}) {
    throw UnsupportedError('이 플랫폼에서는 Live2DController가 지원되지 않습니다.');
  }

  @override
  void playMotion(String group, int index) {}

  @override
  void playAudio(String base64Audio) {}

  @override
  void setMouthOpen(double value) {}

  @override
  void setParameterValue(String id, double value) {}

  @override
  void startLipSync() {}

  @override
  void stopLipSync() {}

  @override
  double getLipSyncValue() => 0.0;

  @override
  void startListeningPose() {}

  @override
  void stopListeningPose() {}

  @override
  void dispose() {}

  @override
  Widget buildView() {
    return const Center(child: Text('Live2D 지원되지 않음'));
  }
}
