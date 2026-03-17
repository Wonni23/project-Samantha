/// 웹 전용 라이브러리를 안드로이드 등 비웹 환경에서 빌드할 때 발생하는
/// 임포트 에러를 방지하기 위한 스텁(Stub) 파일입니다.
library;

// 필요한 모든 타입을 dynamic 또는 가짜 객체로 정의합니다.
class JSObject {}
class JSPromise<T> {}
class JSAny {}
class Window {
  dynamic document;
  dynamic location;
}
class Document {
  dynamic createElement(String tag) => null;
}
class HTMLCanvasElement {}
class HTMLDivElement {}

final dynamic platformViewRegistry = null;
final dynamic window = null;
final dynamic document = null;

class PlatformUtilsImpl {
  static Future<String> getPlayableUrl(dynamic audioData) async => '';
  static void revokeUrl(String url) {}
  static Future<dynamic> fetchBytes(String url) async => null;
}
