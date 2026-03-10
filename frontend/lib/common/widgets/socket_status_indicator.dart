import 'package:flutter/material.dart';
import 'package:frontend/core/network/socket_service.dart';

/// 소켓 연결 상태를 표시하는 공통 인디케이터 위젯
class SocketStatusIndicator extends StatelessWidget {
  final SocketStatus status;

  const SocketStatusIndicator({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    Color color;
    String tooltip;

    switch (status) {
      case SocketStatus.connected:
        color = Colors.greenAccent;
        tooltip = '서버와 연결됨';
        break;
      case SocketStatus.connecting:
        color = Colors.orangeAccent;
        tooltip = '연결 중...';
        break;
      case SocketStatus.disconnected:
        color = Colors.grey;
        tooltip = '연결 끊김';
        break;
      case SocketStatus.error:
        color = Colors.redAccent;
        tooltip = '연결 에러';
        break;
      default:
        color = Colors.transparent;
        tooltip = '';
    }

    return Tooltip(
      message: tooltip,
      child: Container(
        width: 12,
        height: 12,
        decoration: BoxDecoration(
          color: color,
          shape: BoxShape.circle,
          boxShadow: [
            if (status != SocketStatus.initial)
              BoxShadow(
                color: color.withValues(alpha: 0.5),
                blurRadius: 4,
                spreadRadius: 2,
              ),
          ],
        ),
      ),
    );
  }
}
