import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_web_plugins/url_strategy.dart';

import 'package:frontend/app.dart';
import 'package:frontend/core/config/api_config.dart';
import 'package:frontend/core/utils/local_server.dart'; // [신규] 로컬 서버 유틸 임포트

Future<void> main() async {
  // Flutter 바인딩 초기화
  WidgetsFlutterBinding.ensureInitialized();

  // .env 파일 로드
  await ApiConfig.load();

  // [신규] 안드로이드에서 로컬 에셋 서빙을 위한 서버 시작
  if (!kIsWeb) {
    await LocalAssetServer.start();
  }

  // 웹 앱의 URL에서 #을 제거합니다.
  if (kIsWeb) {
    usePathUrlStrategy();
  }

  runApp(const ProviderScope(child: MyApp()));
}
