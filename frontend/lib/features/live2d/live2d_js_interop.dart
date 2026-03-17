import 'dart:js_interop';
import 'package:web/web.dart' as web;

// Live2D Manager JavaScript 객체 정의
@JS()
extension type Live2DManager._(JSObject _) implements JSObject {
  external JSPromise<JSAny?> initialize(String canvasId, String modelPath);
  external void playMotion(String group, int index);
  external void setMouthOpen(double value);
  external void setParameterValue(String id, double value);
  external void startLipSync();
  external void stopLipSync();
  external double getLipSyncValue();
  external void startListeningPose();
  external void stopListeningPose();
  external void destroy();
}

// Window 객체 확장
@JS()
extension type WindowExtension._(web.Window _) implements web.Window {
  external Live2DManager? get live2dManager;
}

extension WindowLive2DExtension on web.Window {
  Live2DManager? get live2dManager => (WindowExtension._(this)).live2dManager;
}
