import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_sound/flutter_sound.dart';

/// 앱 전체에서 공유될 단일 FlutterSoundPlayer 인스턴스를 제공하는 Provider
final soundPlayerProvider = Provider<FlutterSoundPlayer>((ref) {
  final player = FlutterSoundPlayer();

  // Provider가 소멸될 때 플레이어도 함께 닫히도록 설정합니다.
  ref.onDispose(() {
    player.closePlayer();
  });

  return player;
});
