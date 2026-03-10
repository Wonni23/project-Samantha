import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/common/widgets/socket_status_indicator.dart';
import 'package:frontend/core/network/socket_service.dart';

/// 채팅/보이스 모드 전환 탭바와 소켓 상태를 표시하는 위젯
class ModeSwitchTabBar extends ConsumerWidget {
  final TabController tabController;

  const ModeSwitchTabBar({super.key, required this.tabController});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final socketStatus = ref.watch(socketStatusProvider);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 20.0, horizontal: 16.0),
      child: Column(
        children: [
          Row(
            children: [
              const Spacer(),
              SizedBox(
                width: MediaQuery.of(context).size.width * 0.5,
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.grey[300]?.withAlpha(128),
                    borderRadius: BorderRadius.circular(30.0),
                  ),
                  child: TabBar(
                    controller: tabController,
                    dividerColor: Colors.transparent, // 하단 흰색 줄 제거
                    labelColor: Colors.white,
                    unselectedLabelColor: Colors.black,
                    indicatorSize: TabBarIndicatorSize.tab,
                    indicator: BoxDecoration(
                      color: Colors.black,
                      borderRadius: BorderRadius.circular(30.0),
                    ),
                    splashBorderRadius: BorderRadius.circular(30.0),
                    indicatorColor: Colors.blue,
                    tabs: const [
                      Tab(text: '채팅 모드'),
                      Tab(text: '보이스 모드'),
                    ],
                  ),
                ),
              ),
              Expanded(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [SocketStatusIndicator(status: socketStatus)],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
