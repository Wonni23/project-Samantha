import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 테스트 모드 여부를 관리하는 Notifier
class TestModeNotifier extends Notifier<bool> {
  @override
  bool build() => true;

  void toggle() => state = !state;
  void set(bool value) => state = value;
}

final testModeProvider =
    NotifierProvider<TestModeNotifier, bool>(TestModeNotifier.new);
