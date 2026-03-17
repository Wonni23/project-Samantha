/// 안드로이드 빌드 시 에러를 방지하기 위한 Live2D Interop 스텁 파일입니다.
class Live2DManager {
  Future<dynamic> initialize(String canvasId, String modelPath) async => null;
  void playMotion(String group, int index) {}
  void setMouthOpen(double value) {}
  void setParameterValue(String id, double value) {}
  void startLipSync() {}
  void stopLipSync() {}
  double getLipSyncValue() => 0.0;
  void startListeningPose() {}
  void stopListeningPose() {}
  void destroy() {}
}

class WindowLive2DExtension {
  static Live2DManager? getLive2dManager(dynamic window) => null;
}
