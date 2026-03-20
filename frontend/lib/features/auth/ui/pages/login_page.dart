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
  final _phone1Controller = TextEditingController(text: '010');
  final _phone2Controller = TextEditingController();
  final _phone3Controller = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  
  final _phone2Focus = FocusNode();
  final _phone3Focus = FocusNode();
  final _passwordFocus = FocusNode();

  final _formKey = GlobalKey<FormState>();
  bool _showPasswordFields = false;
  bool _isSignUpMode = false;

  @override
  void dispose() {
    _phone1Controller.dispose();
    _phone2Controller.dispose();
    _phone3Controller.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _phone2Focus.dispose();
    _phone3Focus.dispose();
    _passwordFocus.dispose();
    super.dispose();
  }

  String get _fullPhoneNumber => 
      '${_phone1Controller.text}${_phone2Controller.text}${_phone3Controller.text}';

  void _handleContinue() {
    if (_formKey.currentState?.validate() ?? false) {
      setState(() {
        _showPasswordFields = true;
      });
      // 비밀번호 필드로 포커스 이동
      Future.delayed(const Duration(milliseconds: 100), () {
        _passwordFocus.requestFocus();
      });
    }
  }

  void _handleLogin() {
    if (_formKey.currentState?.validate() ?? false) {
      final phoneNumber = _fullPhoneNumber;
      if (_isSignUpMode) {
        ref.read(authProvider.notifier).signUpWithPhone(
              phoneNumber,
              _passwordController.text,
            );
      } else {
        ref.read(authProvider.notifier).signInWithPhone(
              phoneNumber,
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
                      
                      // 핸드폰 번호 입력 영역
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // 1. 통신사 번호 (010 등)
                          Expanded(
                            flex: 2,
                            child: TextFormField(
                              controller: _phone1Controller,
                              keyboardType: TextInputType.phone,
                              textAlign: TextAlign.center,
                              enabled: !isLoading,
                              maxLength: 3,
                              decoration: InputDecoration(
                                counterText: '',
                                hintText: '010',
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                              onChanged: (value) {
                                if (value.length == 3) {
                                  _phone2Focus.requestFocus();
                                }
                              },
                              validator: (value) => (value == null || value.isEmpty) ? '' : null,
                            ),
                          ),
                          const Padding(
                            padding: EdgeInsets.symmetric(horizontal: 8, vertical: 16),
                            child: Text('-', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                          ),
                          // 2. 중간 번호
                          Expanded(
                            flex: 3,
                            child: TextFormField(
                              controller: _phone2Controller,
                              focusNode: _phone2Focus,
                              keyboardType: TextInputType.phone,
                              textAlign: TextAlign.center,
                              enabled: !isLoading,
                              maxLength: 4,
                              decoration: InputDecoration(
                                counterText: '',
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                              onChanged: (value) {
                                if (value.length == 4) {
                                  _phone3Focus.requestFocus();
                                }
                              },
                              validator: (value) => (value == null || value.isEmpty) ? '' : null,
                            ),
                          ),
                          const Padding(
                            padding: EdgeInsets.symmetric(horizontal: 8, vertical: 16),
                            child: Text('-', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                          ),
                          // 3. 끝 번호
                          Expanded(
                            flex: 3,
                            child: TextFormField(
                              controller: _phone3Controller,
                              focusNode: _phone3Focus,
                              keyboardType: TextInputType.phone,
                              textAlign: TextAlign.center,
                              enabled: !isLoading,
                              maxLength: 4,
                              decoration: InputDecoration(
                                counterText: '',
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                              onChanged: (value) {
                                if (value.length == 4 && !isFormVisible) {
                                  _handleContinue();
                                }
                              },
                              validator: (value) => (value == null || value.isEmpty) ? '' : null,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const Text('핸드폰 번호를 입력해주세요', style: TextStyle(color: Colors.grey, fontSize: 12)),
                      
                      if (isFormVisible) ...[
                        const SizedBox(height: 24),
                        // 비밀번호 입력 필드
                        TextFormField(
                          controller: _passwordController,
                          focusNode: _passwordFocus,
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
                            backgroundColor: _isSignUpMode ? Theme.of(context).colorScheme.primary : null,
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
                            _isSignUpMode ? '이미 계정이 있으신가요? 로그인' : '처음이신가요? 핸드폰 번호로 가입하기',
                            style: TextStyle(
                              color: _isSignUpMode ? Colors.grey : Theme.of(context).colorScheme.primary,
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
                          child: const Text('핸드폰 번호로 계속하기'),
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
                          child: Text(
                            '처음이신가요? 핸드폰 번호로 가입하기',
                            style: TextStyle(
                              color: Theme.of(context).colorScheme.primary,
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
