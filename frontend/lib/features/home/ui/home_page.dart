import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/common/widgets/default_layout.dart';
import 'package:frontend/core/network/socket_service.dart';
import 'package:frontend/features/auth/providers/user_provider.dart';
import 'package:frontend/features/chat/ui/chat_screen.dart';
import 'package:frontend/features/home/providers/ai_response_provider.dart';
import 'package:frontend/features/home/providers/audio_recorder_provider.dart';
import 'package:frontend/features/home/ui/widgets/info_widgets.dart';
import 'package:frontend/features/home/ui/widgets/live2d_motion_buttons.dart';
import 'package:frontend/features/home/ui/widgets/mode_switch_tab_bar.dart';
import 'package:frontend/features/home/ui/widgets/voice_mode_controls.dart';
import 'package:frontend/features/live2d/live2d_widget.dart';
import 'package:frontend/features/live2d/providers/live2d_provider.dart';
import 'package:frontend/features/memory/providers/memory_provider.dart';
import 'package:frontend/features/memory/providers/user_context_provider.dart';
import 'package:frontend/features/memory/ui/widgets/memory_view.dart';
import 'package:frontend/features/memory/ui/widgets/user_context_view.dart';
import 'package:flutter/foundation.dart' show kIsWeb;

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage>
    with SingleTickerProviderStateMixin {
  final GlobalKey<Live2DWidgetState> _live2dKey = GlobalKey();
  late TabController _voiceChatTabController;
  int _currentNavIndex = 1;

  void _onPlaybackStarted() {
    final live2dEvent = ref.read(live2DProvider);
    final motionIndex = live2dEvent?.motionIndex ?? 2; // 기본값 2 (serene)
    _live2dKey.currentState?.playMotion('', motionIndex);

    if (kIsWeb) {
      _live2dKey.currentState?.startLipSync();
    }
  }

  void _onPlaybackStopped() {
    if (kIsWeb) {
      _live2dKey.currentState?.stopLipSync();
    }
  }

  @override
  void initState() {
    super.initState();
    // SocketService 초기화 (Future.microtask를 사용하여 빌드 완료 후 실행)
    Future.microtask(() async {
      if (!mounted) return;
      await ref.read(socketServiceProvider).init();
      
      // [신규] 초기 로드 흐름 제어
      // 1. m2 (뒷짐 자세) 재생은 이제 live2d_init.js에서 모델 로드 즉시 수행함 (인덱스 0)
      
      // 2. m8 (인사) 재생 (기존 800ms -> 1000ms로 조정하여 m2 노출 시간 확보)
      await Future.delayed(const Duration(milliseconds: 1000));
      if (mounted) {
        _live2dKey.currentState?.playMotion('', 8);
      }
    });

    _voiceChatTabController = TabController(
      length: 2,
      vsync: this,
      initialIndex: 1,
    );
    _voiceChatTabController.addListener(() {
      if (mounted) {
        setState(() {}); // Rebuild to switch between chat and voice UI
      }
    });
  }

  @override
  void dispose() {
    _voiceChatTabController.dispose();
    // SocketService 해제는 Provider의 onDispose에서 자동 처리되므로 명시적 호출 제거
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // 에러 발생 시 SnackBar 표시
    ref.listen<String?>(socketErrorProvider, (previous, next) {
      if (next != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(next),
            backgroundColor: Colors.redAccent,
            duration: const Duration(seconds: 3),
            action: SnackBarAction(
              label: '닫기',
              textColor: Colors.white,
              onPressed: () {
                ref.read(socketErrorProvider.notifier).clear();
              },
            ),
          ),
        );
        ref.read(socketErrorProvider.notifier).clear();
      }
    });

    return DefaultLayout(
      // 하단 네비게이션 바 추가
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentNavIndex,
        onDestinationSelected: (index) {
          setState(() {
            _currentNavIndex = index;
          });
          // 기억 탭(index 0)으로 이동할 때마다 데이터 갱신
          if (index == 0) {
            ref.invalidate(memoryProvider);
          }
          // 컨텍스트 탭(index 3)으로 이동할 때마다 데이터 갱신
          if (index == 3) {
            ref.invalidate(userContextProvider);
          }
        },
        destinations: const [
          NavigationDestination(icon: Icon(Icons.psychology), label: '기억'),
          NavigationDestination(icon: Icon(Icons.face), label: '사만다'),
          NavigationDestination(icon: Icon(Icons.person), label: '마이페이지'),
          NavigationDestination(icon: Icon(Icons.hub), label: '컨텍스트'),
        ],
      ),
      child: IndexedStack(
        index: _currentNavIndex,
        children: [
          _buildMemoryTab(),
          _buildLive2DTab(),
          _buildMyPageTab(),
          _buildContextTab(),
        ],
      ),
    );
  }

  /// 1. 라이브2D 탭 (기존 홈 화면)
  Widget _buildLive2DTab() {
    // AI 오디오 재생 상태 리스너
    ref.listen<AIResponseState>(aIResponseProvider, (previous, next) {
      if (previous?.isAudioPlaying == next.isAudioPlaying) {
        return;
      }

      if (next.isAudioPlaying) {
        _onPlaybackStarted();
      } else {
        _onPlaybackStopped();
      }
    });

    // 오디오 상태 리스너 (녹음/미리듣기 사이드 이펙트)
    ref.listen<AudioRecorderState>(audioRecorderProvider, (previous, next) {
      // 녹음 상태 변화 감지
      if (previous?.isRecording != next.isRecording) {
        if (next.isRecording) {
          // 녹음 시작 시 '귀 기울이는 자세' (m27)
          _live2dKey.currentState?.startListeningPose();
        } else {
          // 녹음 중지 시 자세 해제
          _live2dKey.currentState?.stopListeningPose();
        }
      }

      // 녹음 미리듣기 재생 상태 변화 감지
      if (previous?.isPlaying != next.isPlaying) {
        if (next.isPlaying) {
          _onPlaybackStarted();
        } else {
          _onPlaybackStopped();
        }
      }
    });

    return Column(
      children: [
        Expanded(
          child: Stack(
            alignment: Alignment.center,
            children: [
              Live2DWidget(
                key: _live2dKey,
                modelPath: 'live2d_model/haru_greeter_t05.model3.json',
                width: double.infinity,
                height: double.infinity,
              ),

              // [신규] 현재 감정 상태 텍스트 표시 (좌측 상단)
              Positioned(
                top: 100,
                left: 20,
                child: Consumer(
                  builder: (context, ref, child) {
                    final live2dEvent = ref.watch(live2DProvider);
                    final hasEvent = live2dEvent != null;
                    final expression = live2dEvent?.expression ?? 'serene';
                    
                    return Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: Colors.black.withAlpha(100),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: Colors.white10),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.psychology, 
                            size: 16, 
                            color: hasEvent ? Colors.purpleAccent : Colors.grey,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            expression.toUpperCase(),
                            style: TextStyle(
                              color: hasEvent ? Colors.white : Colors.grey,
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 1.2,
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),

              // [신규] 탭 바를 라이브2D 컨테이너 내부 상단으로 이동
              Positioned(
                top: 0,
                left: 0,
                right: 0,
                child: ModeSwitchTabBar(tabController: _voiceChatTabController),
              ),

              Live2DMotionButtons(live2dKey: _live2dKey),

              if (_voiceChatTabController.index == 0)
                const Positioned(
                  top: 80, // 상단 탭 바 아래에 위치하도록 조정
                  left: 0,
                  right: 0,
                  bottom: 0,
                  child: ChatScreen(),
                )
              else
                const Positioned(bottom: 40, child: VoiceModeControls()),
            ],
          ),
        ),
      ],
    );
  }

  /// 2. 마이페이지 탭
  Widget _buildMyPageTab() {
    final userAsync = ref.watch(userInfoProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: const Text('내 정보', style: TextStyle(color: Colors.black87, fontWeight: FontWeight.bold)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.black87),
            onPressed: () => ref.read(userInfoProvider.notifier).refresh(),
          ),
        ],
      ),
      body: userAsync.when(
        data: (user) {
          if (user == null) {
            return const Center(
              child: Text(
                '사용자 정보를 불러올 수 없습니다.',
                style: TextStyle(color: Colors.black87),
              ),
            );
          }
          return ListView(
            padding: const EdgeInsets.all(20),
            children: [
              InfoCard(
                title: '기본 정보',
                children: [
                  InfoTile(icon: Icons.person, label: '이름', value: user.realName ?? '미설정'),
                  InfoTile(icon: Icons.phone, label: '전화번호', value: user.phoneNumber ?? '미설정'),
                  InfoTile(
                    icon: Icons.wc,
                    label: '성별',
                    value: _formatGender(user.gender),
                  ),
                  InfoTile(
                    icon: Icons.cake,
                    label: '출생연도',
                    value: user.birthYear?.toString() ?? '미설정',
                  ),
                ],
              ),
              const SizedBox(height: 20),
              InfoCard(
                title: '계정 정보',
                children: [
                  InfoTile(icon: Icons.stars, label: '등급', value: user.tier.toUpperCase()),
                  InfoTile(
                    icon: Icons.access_time,
                    label: '오늘 사용량',
                    value: '${user.dailyUsage}분',
                  ),
                  InfoTile(
                    icon: Icons.location_on,
                    label: '지역',
                    value: user.addressDistrict ?? '미설정',
                  ),
                ],
              ),
            ],
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => const Center(
          child: Text('내 정보를 불러오는 중 오류가 발생했습니다.', style: TextStyle(color: Colors.black87)),
        ),
      ),
    );
  }

  /// 성별 데이터를 한글로 변환합니다.
  String _formatGender(String? gender) {
    if (gender == null) return '미설정';
    final g = gender.toLowerCase();
    if (g == 'male') return '남성';
    if (g == 'female') return '여성';
    return '미설정';
  }

  /// 3. 기억 탭
  Widget _buildMemoryTab() {
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: const Text('기억 보관함', style: TextStyle(color: Colors.black87, fontWeight: FontWeight.bold)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.black87),
            onPressed: () => ref.read(memoryProvider.notifier).refresh(),
          ),
        ],
      ),
      body: const MemoryView(),
    );
  }

  /// 4. 컨텍스트 탭
  Widget _buildContextTab() {
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: const Text('사용자 컨텍스트', style: TextStyle(color: Colors.black87, fontWeight: FontWeight.bold)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.black87),
            onPressed: () => ref.read(userContextProvider.notifier).refresh(),
          ),
        ],
      ),
      body: const UserContextView(),
    );
  }
}
