import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_web_plugins/url_strategy.dart';

import 'package:frontend/app.dart';
import 'package:frontend/core/config/api_config.dart';

Future<void> main() async {
  // Flutter 바인딩 초기화
  WidgetsFlutterBinding.ensureInitialized();

  // .env 파일 로드
  await ApiConfig.load();

  // 웹 앱의 URL에서 #을 제거합니다.
  usePathUrlStrategy();

  runApp(const ProviderScope(child: MyApp()));
}
