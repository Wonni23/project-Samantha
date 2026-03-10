import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/providers/test_mode_provider.dart';
import 'package:frontend/common/widgets/default_layout.dart';
import 'package:frontend/features/auth/providers/social_login_provider.dart';
import 'package:frontend/features/auth/ui/widgets/social_login_button.dart';
import 'package:flutter/material.dart';
import 'package:frontend/features/auth/providers/auth_provider.dart';
import 'package:go_router/go_router.dart';
import 'package:frontend/core/router/router_paths.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _showPasswordFields = false;
  bool _isSignUpMode = false;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  void _handleContinue() {
    if (_formKey.currentState?.validate() ?? false) {
      setState(() {
        _showPasswordFields = true;
      });
    }
  }

  void _handleLogin() {
    if (_formKey.currentState?.validate() ?? false) {
      if (_isSignUpMode) {
        ref.read(authProvider.notifier).signUpWithEmail(
              _emailController.text.trim(),
              _passwordController.text,
            );
      } else {
        ref.read(authProvider.notifier).signInWithEmail(
              _emailController.text.trim(),
              _passwordController.text,
            );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final isLoading = authState.isLoading;

    ref.listen(authProvider, (previous, next) {
      next.when(
        data: (_) {},
        error: (error, stackTrace) {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(error.toString()),
              backgroundColor: Colors.redAccent,
              duration: const Duration(seconds: 4),
            ),
          );
        },
        loading: () {},
      );
    });

    // 회원가입 모드이거나, 로그인 과정에서 '계속하기'를 눌러 비밀번호 창이 활성화된 경우
    final bool isFormVisible = _isSignUpMode || _showPasswordFields;

    return DefaultLayout(
      child: Stack(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24.0),
            child: Form(
              key: _formKey,
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 500),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Spacer(),
                      
                      // 이메일 입력 필드
                      TextFormField(
                        controller: _emailController,
                        keyboardType: TextInputType.emailAddress,
                        enabled: !isLoading,
                        decoration: InputDecoration(
                          hintText: '이메일 주소',
                          prefixIcon: const Icon(Icons.email_outlined),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) return '이메일을 입력해주세요.';
                          if (!RegExp(r'^[^@]+@[^@]+\.[^@]+$').hasMatch(value)) {
                            return '유효한 이메일 형식이 아닙니다.';
                          }
                          return null;
                        },
                      ),
                      
                      if (isFormVisible) ...[
                        const SizedBox(height: 16),
                        // 비밀번호 입력 필드
                        TextFormField(
                          controller: _passwordController,
                          obscureText: true,
                          enabled: !isLoading,
                          decoration: InputDecoration(
                            hintText: '비밀번호',
                            prefixIcon: const Icon(Icons.lock_outline),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                          validator: (value) {
                            if (value == null || value.isEmpty) return '비밀번호를 입력해주세요.';
                            if (_isSignUpMode) {
                              if (value.length < 8) return '비밀번호는 8자 이상이어야 합니다.';
                              if (!RegExp(r'[A-Z]').hasMatch(value)) return '대문자를 포함해야 합니다.';
                              if (!RegExp(r'[a-z]').hasMatch(value)) return '소문자를 포함해야 합니다.';
                              if (!RegExp(r'[!@#$%^&*(),.?":{}|<>]').hasMatch(value)) return '특수문자를 포함해야 합니다.';
                            }
                            return null;
                          },
                        ),
                        
                        if (_isSignUpMode) ...[
                          const SizedBox(height: 16),
                          // 비밀번호 확인 필드 (회원가입 모드 전용)
                          TextFormField(
                            controller: _confirmPasswordController,
                            obscureText: true,
                            enabled: !isLoading,
                            decoration: InputDecoration(
                              hintText: '비밀번호 확인',
                              prefixIcon: const Icon(Icons.lock_reset_outlined),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) return '비밀번호를 다시 입력해주세요.';
                              if (value != _passwordController.text) return '비밀번호가 일치하지 않습니다.';
                              return null;
                            },
                          ),
                        ],

                        const SizedBox(height: 24),
                        ElevatedButton(
                          onPressed: isLoading ? null : _handleLogin,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _isSignUpMode ? Colors.deepPurple : null,
                            foregroundColor: _isSignUpMode ? Colors.white : null,
                            minimumSize: const Size(double.infinity, 56),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                          child: Text(_isSignUpMode ? '회원가입 완료' : '로그인'),
                        ),
                        const SizedBox(height: 8),
                        TextButton(
                          onPressed: () {
                            setState(() {
                              _isSignUpMode = !_isSignUpMode;
                              _passwordController.clear();
                              _confirmPasswordController.clear();
                              // 로그인 모드로 전환 시에는 다시 '계속하기' 버튼이 보이도록 초기화
                              if (!_isSignUpMode) {
                                _showPasswordFields = false;
                              }
                            });
                          },
                          child: Text(
                            _isSignUpMode ? '이미 계정이 있으신가요? 로그인' : '처음이신가요? 이메일로 가입하기',
                            style: TextStyle(
                              color: _isSignUpMode ? Colors.grey : Colors.deepPurple,
                              fontWeight: _isSignUpMode ? null : FontWeight.bold,
                            ),
                          ),
                        ),
                      ] else ...[
                        const SizedBox(height: 24),
                        ElevatedButton(
                          onPressed: isLoading ? null : _handleContinue,
                          style: ElevatedButton.styleFrom(
                            minimumSize: const Size(double.infinity, 56),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                          child: const Text('이메일로 계속하기'),
                        ),
                        const SizedBox(height: 8),
                        TextButton(
                          onPressed: () {
                            setState(() {
                              _isSignUpMode = true;
                              _passwordController.clear();
                              _confirmPasswordController.clear();
                            });
                          },
                          child: const Text(
                            '처음이신가요? 이메일로 가입하기',
                            style: TextStyle(
                              color: Colors.deepPurple,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],

                      const SizedBox(height: 32),
                      const Row(
                        children: [
                          Expanded(child: Divider()),
                          Padding(
                            padding: EdgeInsets.symmetric(horizontal: 16),
                            child: Text('또는', style: TextStyle(color: Colors.grey)),
                          ),
                          Expanded(child: Divider()),
                        ],
                      ),
                      const SizedBox(height: 32),

                      ...SocialLoginProvider.values.map((provider) {
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8.0),
                          child: SocialLoginButton(
                            text: provider.text,
                            logoAsset: provider.logoAsset,
                            backgroundColor: provider.backgroundColor,
                            textColor: provider.textColor,
                            onPressed: isLoading
                                ? null
                                : () {
                                    if (provider == SocialLoginProvider.google) {
                                      ref.read(authProvider.notifier).signInWithGoogle();
                                    } else if (provider == SocialLoginProvider.kakao) {
                                      ref.read(authProvider.notifier).signInWithKakao();
                                    } else if (provider == SocialLoginProvider.naver) {
                                      ref.read(authProvider.notifier).signInWithNaver();
                                    }
                                  },
                          ),
                        );
                      }),
                      
                      if (!const bool.fromEnvironment('dart.vm.product'))
                        Padding(
                          padding: const EdgeInsets.only(top: 16.0),
                          child: Center(
                            child: ElevatedButton(
                              onPressed: () {
                                ref.read(testModeProvider.notifier).set(true);
                                context.go(AppRoutePaths.home);
                              },
                              child: const Text('홈으로 (테스트)'),
                            ),
                          ),
                        ),
                      const Spacer(),
                    ],
                  ),
                ),
              ),
            ),
          ),
          if (isLoading)
            Container(
              color: Colors.black.withValues(alpha: 0.5),
              child: const Center(child: CircularProgressIndicator()),
            ),
        ],
      ),
    );
  }
}
