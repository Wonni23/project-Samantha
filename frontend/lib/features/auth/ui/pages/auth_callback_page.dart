import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:frontend/features/auth/providers/auth_provider.dart';

/// OAuth 콜백을 처리하는 페이지
/// 
/// OAuth Provider에서 인증 완료 후 이 페이지로 리디렉션됩니다.
/// URL에서 인증 코드를 추출하여 백엔드로 전송하고 로그인을 완료합니다.
class AuthCallbackPage extends ConsumerStatefulWidget {
  const AuthCallbackPage({super.key});

  @override
  ConsumerState<AuthCallbackPage> createState() => _AuthCallbackPageState();
}

class _AuthCallbackPageState extends ConsumerState<AuthCallbackPage> {
  @override
  void initState() {
    super.initState();
    // 위젯이 빌드된 후 OAuth 콜백 처리
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _handleOAuthCallback();
    });
  }

  Future<void> _handleOAuthCallback() async {
    try {
      // Auth Provider의 콜백 핸들러 호출
      await ref.read(authProvider.notifier).handleOAuthCallback();

      // 상태 업데이트가 완전히 반영될 때까지 짧게 대기
      await Future.delayed(const Duration(milliseconds: 100));

      if (!mounted) return; // 추가: 위젯이 마운트 해제되었다면 즉시 반환

      // 최종 상태 확인
      final authState = ref.read(authProvider);

      if (authState.hasValue) {
        final status = authState.requireValue;

        // 로그인 성공 또는 온보딩 필요 상태면 router의 redirect 로직이 자동으로 처리
        // 명시적으로 네비게이션하지 않고 router가 redirect하도록 함
        if (status == AuthStatus.loggedIn || status == AuthStatus.onboardingRequired) {
          if (!mounted) return; // 추가: context.go() 호출 전에 mounted 체크
          context.go('/');
        }
      }
    } catch (e) {
      // 에러 발생 시 로그인 페이지로 이동
      if (!mounted) return; // 추가: 위젯이 마운트 해제되었다면 즉시 반환
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('로그인 중 오류가 발생했습니다. 다시 시도해 주세요.'),
          backgroundColor: Colors.red,
          duration: Duration(seconds: 5),
        ),
      );
      // 잠시 대기 후 로그인 페이지로 이동
      await Future.delayed(const Duration(milliseconds: 1000));
      if (!mounted) return; // 추가: 대기 후에도 mounted 체크
      context.go('/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text(
              '로그인 처리 중...',
              style: TextStyle(fontSize: 16),
            ),
          ],
        ),
      ),
    );
  }
}
