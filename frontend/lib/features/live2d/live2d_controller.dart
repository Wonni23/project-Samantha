import 'package:flutter/material.dart';

// 플랫폼별 조건부 임포트 - 웹용은 js_interop 라이브러리가 존재할 때만, 
// 모바일용은 dart:io 라이브러리가 존재할 때만 선택됩니다.
import 'live2d_controller_stub.dart'
    if (dart.library.js_interop) 'live2d_web_impl.dart'
    if (dart.library.io) 'live2d_mobile_impl.dart';

/// Live2D 캐릭터를 제어하기 위한 공통 인터페이스입니다.
abstract class Live2DController {
  /// 플랫폼별 적절한 구현체를 생성하는 팩토리 메서드
  factory Live2DController(String viewId, String canvasId, String modelPath, {VoidCallback? onPlaybackFinished}) {
    return Live2DControllerImpl(viewId, canvasId, modelPath, onPlaybackFinished: onPlaybackFinished);
  }

  VoidCallback? onPlaybackFinished;

  void playMotion(String group, int index);
  void playAudio(String base64Audio);
  void setMouthOpen(double value);
  void setParameterValue(String id, double value);
  void startLipSync();
  void stopLipSync();
  double getLipSyncValue();
  void startListeningPose();
  void stopListeningPose();
  void dispose();

  /// 플랫폼에 맞는 뷰 위젯을 반환합니다.
  Widget buildView();
}
