import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:frontend/features/auth/providers/social_login_provider.dart';

import 'package:frontend/features/auth/ui/pages/login_page.dart';
import 'package:frontend/features/auth/ui/pages/auth_callback_page.dart';
import 'package:frontend/features/auth/ui/pages/onboarding_page.dart';
import 'package:frontend/features/auth/ui/pages/onboarding_terms_page.dart';
import 'package:frontend/features/auth/providers/auth_provider.dart';
import 'features/home/ui/home_page.dart';
import 'core/router/router_paths.dart';
import 'core/providers/test_mode_provider.dart';
import 'features/legal/ui/privacy_policy_page.dart';
import 'features/legal/ui/terms_of_service_page.dart';
import 'features/memory/ui/pages/memory_page.dart';
import 'common/widgets/no_transitions_builder.dart';

/// GoRouter의 상태 변경을 알리는 Notifier
/// authProvider나 testModeProvider가 변할 때마다 리디렉션 로직을 실행하도록 트리거합니다.
class RouterNotifier extends ChangeNotifier {
  final Ref _ref;

  RouterNotifier(this._ref) {
    _ref.listen<AsyncValue<AuthStatus>>(
      authProvider,
      (previous, next) => notifyListeners(),
    );
    _ref.listen<bool>(
      testModeProvider,
      (previous, next) => notifyListeners(),
    );
  }
}

final routerNotifierProvider = Provider<RouterNotifier>((ref) {
  final notifier = RouterNotifier(ref);
  // [리뷰 반영] Notifier 소멸 시 리소스 정리
  ref.onDispose(notifier.dispose);
  return notifier;
});

final routerProvider = Provider<GoRouter>((ref) {
  // notifier를 read하여 GoRouter 인스턴스가 재생성되는 것을 방지합니다.
  final notifier = ref.read(routerNotifierProvider);

  return GoRouter(
    initialLocation: AppRoutePaths.home,
    refreshListenable: notifier,
    redirect: (context, state) {
      // 리디렉션 판단 시에는 최신 상태를 read하여 사용합니다.
      final isTestMode = ref.read(testModeProvider);
      if (isTestMode) {
        return null; 
      }

      final authState = ref.read(authProvider);
      
      // authProvider가 아직 로딩 중이면 스플래시 화면으로 보냄
      if (authState.isLoading || authState.isRefreshing) {
        // 로그인 페이지나 콜백 경로에 있을 때는 스플래시로 보내지 않음 (로그인/회원가입 진행 중인 경우)
        final location = state.matchedLocation;
        if (location == AppRoutePaths.login || location == '/auth/callback') {
          return null;
        }
        return '/splash';
      }
      
      // 에러 발생 시 처리 강화
      if (authState.hasError) {
        // 로그인 페이지에서 에러가 발생한 경우라면 리디렉션하지 않고 메시지를 보여줌
        if (state.matchedLocation == AppRoutePaths.login) {
          return null;
        }
        // 그 외의 경우에만 로그인 페이지로 보냄
        return AppRoutePaths.login;
      }

      // [수정] valueOrNull 대신 value 사용 (호환성 확보)
      final status = authState.value;
      if (status == null) {
        return state.matchedLocation == AppRoutePaths.login ? null : AppRoutePaths.login;
      }

      final location = state.matchedLocation;

      // 현재 경로가 스플래시/로그인 관련 페이지인지 확인
      final isAuthRoute = location == AppRoutePaths.login ||
          location == '/auth/callback' ||
          location == '/splash';
      // 현재 경로가 온보딩 관련 페이지인지 확인
      final isOnboardingRoute = location.startsWith('/onboarding');

      switch (status) {
        case AuthStatus.loggedOut:
          // 로그아웃 상태에서는 로그인/콜백 페이지 외의 모든 접근을 로그인 페이지로 리디렉션
          return isAuthRoute ? null : AppRoutePaths.login;
        case AuthStatus.onboardingRequired:
          // 온보딩 필요 상태에서는 온보딩 관련 경로가 아니면 프로필 설정 페이지로 리디렉션
          return isOnboardingRoute ? null : AppRoutePaths.onboardingProfile;
        case AuthStatus.loggedIn:
          // 로그인 완료 상태에서는 인증/온보딩 관련 페이지 접근 시 홈으로 리디렉션
          return (isAuthRoute || isOnboardingRoute) ? AppRoutePaths.home : null;
      }
    },
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) =>
            const Scaffold(body: Center(child: CircularProgressIndicator())),
      ),
      GoRoute(
        path: AppRoutePaths.login,
        builder: (context, state) => const LoginPage(),
      ),
      // OAuth 콜백 라우트 추가
      GoRoute(
        path: '/auth/callback',
        builder: (context, state) => const AuthCallbackPage(),
      ),
      GoRoute(
        path: AppRoutePaths.onboardingProfile,
        builder: (context, state) => const OnboardingProfilePage(),
      ),
      GoRoute(
        path: AppRoutePaths.onboardingTerms,
        builder: (context, state) {
          return const OnboardingTermsPage();
        },
      ),
      
      // 메인 서비스 경로들을 StatefulShellRoute로 감싸 상태를 보존합니다.
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) {
          return navigationShell;
        },
        branches: [
          // 브랜치 1: 홈 (사만다 대화 및 Live2D)
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutePaths.home, // 상수 사용
                builder: (context, state) => const HomePage(),
              ),
            ],
          ),
          // 브랜치 2: 기억 보관함
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutePaths.memory,
                builder: (context, state) => const MemoryPage(),
              ),
            ],
          ),
          // 브랜치 3: 약관 및 정책 (홈에서 이동 시 홈 상태 보존을 위해 별도 브랜치로 구성)
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutePaths.privacyPolicy,
                builder: (context, state) => const PrivacyPolicyPage(),
              ),
              GoRoute(
                path: AppRoutePaths.termsOfService,
                builder: (context, state) => const TermsOfServicePage(),
              ),
            ],
          ),
        ],
      ),
    ],
  );
});

class MyApp extends ConsumerStatefulWidget {
  const MyApp({super.key});

  @override
  ConsumerState<MyApp> createState() => _MyAppState();
}

class _MyAppState extends ConsumerState<MyApp> {
  late final Future<void> _initialization;

  @override
  void initState() {
    super.initState();
    // 앱 시작 시 필요한 모든 비동기 초기화를 여기서 수행합니다.
    _initialization = _precacheSvgs();
  }

  /// SVG 이미지를 미리 캐시하여 로딩 속도를 개선하고 Future를 반환합니다.
  Future<void> _precacheSvgs() async {
    final futures = <Future<void>>[];
    for (final provider in SocialLoginProvider.values) {
      final loader = SvgAssetLoader(provider.logoAsset);
      futures.add(
        svg.cache.putIfAbsent(
          loader.cacheKey(null),
          () => loader.loadBytes(null),
        ),
      );
    }
    // 모든 SVG 캐싱이 완료될 때까지 기다립니다.
    await Future.wait(futures);
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      routerConfig: router,
      title: 'project Samantha',
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF6D4C41), // 딥 브론즈 (Seed)
          surface: const Color(0xFFEFEBE0),   // 코지 오트밀 (Base Background)
          onSurface: const Color(0xFF3E2723), // 차콜 브라운 (Text)
          primary: const Color(0xFF6D4C41),
          secondary: const Color(0xFF8E9775), // 세이지 그린 (Accent)
        ),
        scaffoldBackgroundColor: const Color(0xFFEFEBE0),
        fontFamily: 'Noto Sans KR',
        textTheme: const TextTheme(
          bodyLarge: TextStyle(color: Color(0xFF3E2723)),
          bodyMedium: TextStyle(color: Color(0xFF3E2723)),
          titleLarge: TextStyle(color: Color(0xFF3E2723), fontWeight: FontWeight.bold),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFFEFEBE0),
          foregroundColor: Color(0xFF3E2723),
          elevation: 0,
          centerTitle: true,
        ),
        pageTransitionsTheme: PageTransitionsTheme(
          builders: kIsWeb
              ? {
                  // 웹에서 실행 중인 경우 모든 플랫폼에 대해 NoTransitionsBuilder를 사용
                  for (final platform in TargetPlatform.values)
                    platform: const NoTransitionsBuilder(),
                }
              : {
                  TargetPlatform.android: const ZoomPageTransitionsBuilder(),
                  TargetPlatform.iOS: const ZoomPageTransitionsBuilder(),
                  TargetPlatform.fuchsia: const ZoomPageTransitionsBuilder(),
                  TargetPlatform.linux: const ZoomPageTransitionsBuilder(),
                  TargetPlatform.macOS: const ZoomPageTransitionsBuilder(),
                  TargetPlatform.windows: const ZoomPageTransitionsBuilder(),
                },
        ),
      ),
      // GoRouter의 모든 페이지 위에 위젯을 추가(여기서는 로딩 화면)
      builder: (context, child) {
        return FutureBuilder(
          future: _initialization,
          builder: (context, snapshot) {
            // 초기화 진행 중 로딩 화면 표시
            if (snapshot.connectionState != ConnectionState.done) {
              return const Scaffold(
                body: Center(child: CircularProgressIndicator()),
              );
            }

            // 초기화 중 에러 발생
            if (snapshot.hasError) {
              return Scaffold(
                body: Center(
                  child: Text('앱 초기화 중 오류가 발생했습니다: ${snapshot.error}'),
                ),
              );
            }

            // 초기화 완료 후, GoRouter가 보내준 페이지(child)를 표시
            return child!;
          },
        );
      },
    );
  }
}
