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
                    color: const Color(0xFFE5E0D5), // 배경보다 살짝 어두운 톤으로 입체감 부여
                    borderRadius: BorderRadius.circular(30.0),
                  ),
                  child: TabBar(
                    controller: tabController,
                    dividerColor: Colors.transparent, // 하단 흰색 줄 제거
                    labelColor: Colors.white,
                    unselectedLabelColor: const Color(0xFF8D8171), // 뮤트 브라운
                    indicatorSize: TabBarIndicatorSize.tab,
                    indicator: BoxDecoration(
                      color: const Color(0xFF333333), // 소프트 차콜
                      borderRadius: BorderRadius.circular(30.0),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withAlpha(20),
                          blurRadius: 4,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    splashBorderRadius: BorderRadius.circular(30.0),
                    tabs: const [
                      Tab(
                        child: Text(
                          '채팅 모드',
                          style: TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                      Tab(
                        child: Text(
                          '보이스 모드',
                          style: TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
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
