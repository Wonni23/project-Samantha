import 'package:flutter/material.dart';

// 애니메이션 없이 페이지를 전환하는 사용자 정의 PageTransitionsBuilder
class NoTransitionsBuilder extends PageTransitionsBuilder {
  const NoTransitionsBuilder();

  @override
  Widget buildTransitions<T>(
    PageRoute<T>? route,
    BuildContext? context,
    Animation<double> animation,
    Animation<double> secondaryAnimation,
    Widget? child,
  ) {
    // 애니메이션 없이 자식 위젯만 반환합니다.
    return child!;
  }
}
