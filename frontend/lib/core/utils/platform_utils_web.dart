import 'dart:js_interop';
import 'dart:typed_data';
import 'package:web/web.dart' as web;

class PlatformUtilsImpl {
  static Future<String> getPlayableUrl(Uint8List audioData) async {
    final blob = web.Blob(
      [audioData.buffer.toJS].toJS,
      web.BlobPropertyBag(type: 'audio/mpeg'),
    );
    final url = web.URL.createObjectURL(blob);
    return url;
  }

  static void revokeUrl(String url) {
    if (url.startsWith('blob:')) {
      web.URL.revokeObjectURL(url);
    }
  }

  static Future<Uint8List?> fetchBytes(String url) async {
    final web.Response response = await web.window.fetch(url.toJS).toDart;
    final web.Blob blob = await response.blob().toDart;
    final JSArrayBuffer arrayBuffer = await blob.arrayBuffer().toDart;
    return arrayBuffer.toDart.asUint8List();
  }
}
