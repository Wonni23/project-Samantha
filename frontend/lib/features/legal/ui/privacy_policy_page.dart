import 'package:flutter/material.dart';

import 'package:frontend/common/widgets/header.dart';
import 'package:frontend/features/legal/ui/widgets/legal_page_helpers.dart';

class PrivacyPolicyPage extends StatelessWidget {
  const PrivacyPolicyPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const Header(title: '개인정보 처리방침'),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '최종 수정일: 2026년 2월 23일',
              style: TextStyle(
                fontStyle: FontStyle.italic,
                color: Colors.black54,
              ),
            ),
            const SizedBox(height: 24),
            buildParagraph(
              '주식회사 Samantha(이하 ‘회사’)는 사용자의 개인정보를 매우 중요하게 생각하며, 「개인정보 보호법」 등 관련 법규를 준수하고 있습니다. 회사는 본 개인정보 처리방침을 통해 사용자가 제공하는 개인정보가 어떠한 용도와 방식으로 이용되고 있으며, 개인정보 보호를 위해 어떠한 조치가 취해지고 있는지 알려드립니다.',
            ),
            buildSection(
              title: '제1조 (수집하는 개인정보의 항목 및 수집 방법)',
              children: [
                buildParagraph('1. 회사는 서비스 제공을 위해 필요한 최소한의 개인정보를 수집합니다.'),
                buildListItem('필수 항목: 이름, 출생년도, 성별, 이메일 주소(소셜 로그인 시 제공)'),
                buildListItem('선택 항목: 사용자가 설정하는 호칭'),
                buildListItem(
                  '서비스 이용 과정에서 자동 수집: 기기 정보(OS, 기기 종류), 접속 로그, 쿠키, IP 주소, 서비스 이용 기록',
                ),
                buildParagraph(
                  '2. AI 음성 대화 기능 사용 시, 다음과 같은 음성 관련 데이터가 수집될 수 있습니다.',
                ),
                buildListItem(
                  '수집 항목: 사용자의 발화 음성 데이터 및 변환된 텍스트 데이터',
                ),
                buildListItem('수집 방법: 서비스 내 마이크 기능을 통해 사용자가 직접 입력 시'),
              ],
            ),
            buildSection(
              title: '제2조 (개인정보의 수집 및 이용 목적)',
              children: [
                buildListItem(
                  '회원 관리: 회원 가입 의사 확인, 연령 확인, 본인 식별 및 인증, 불량 회원 제재',
                ),
                buildListItem(
                  '서비스 제공 및 개선: AI 대화 기능 제공, 개인화 서비스(호칭 사용 등) 제공, 서비스 품질 향상을 위한 데이터 분석 및 연구, 신규 기능 개발',
                ),
                buildListItem('고객 지원: 문의사항 및 불만 처리, 공지사항 전달'),
                buildListItem(
                  '마케팅 및 광고 활용 (선택 동의 시): 신규 서비스, 이벤트, 맞춤형 혜택 정보 제공',
                ),
                buildListItem(
                  '음성 데이터의 이용 목적: 사용자의 명령 및 질문 인식, AI 모델의 음성 인식 정확도 향상을 위한 학습',
                ),
              ],
            ),
            buildSection(
              title: '제3조 (개인정보의 보유 및 이용 기간)',
              children: [
                buildParagraph(
                  '회사는 원칙적으로 개인정보 수집 및 이용 목적이 달성된 후에는 해당 정보를 지체 없이 파기합니다. 단, 다음의 정보에 대해서는 아래의 이유로 명시한 기간 동안 보존합니다.',
                ),
                buildListItem(
                  '회원 정보: 회원 탈퇴 시까지. 단, 법령 위반에 따른 수사나 조사가 필요한 경우 해당 절차 종료 시까지',
                ),
                buildListItem(
                  '음성 데이터: 음성 인식 기술 향상을 위해 비식별화 조치 후 최대 3년까지 보관될 수 있으며, 사용자는 언제든지 자신의 데이터 삭제를 요청할 수 있습니다.',
                ),
                buildListItem(
                  '법령에 따른 보관: 전자상거래법, 통신비밀보호법 등 관련 법령의 규정에 의하여 보존할 필요가 있는 경우, 회사는 관계 법령에서 정한 일정한 기간 동안 회원정보를 보관합니다.',
                ),
              ],
            ),
            buildSection(
              title: '제4조 (개인정보의 제3자 제공)',
              children: [
                buildParagraph(
                  '회사는 사용자의 동의 없이 개인정보를 외부에 제공하지 않습니다. 단, 아래의 경우에는 예외로 합니다.',
                ),
                buildListItem('사용자가 사전에 동의한 경우'),
                buildListItem(
                  '법령의 규정에 의거하거나, 수사 목적으로 법령에 정해진 절차와 방법에 따라 수사기관의 요구가 있는 경우',
                ),
              ],
            ),
            buildSection(
              title: '제5조 (개인정보 처리의 위탁)',
              children: [
                buildParagraph(
                  '회사는 원활한 서비스 제공을 위해 다음과 같이 개인정보 처리 업무를 외부 전문업체에 위탁하여 운영하고 있습니다.',
                ),
                buildListItem('클라우드 인프라 운영: Amazon Web Services, Inc.'),
                buildListItem('음성 인식 처리: Google Cloud (Speech-to-Text API)'),
                buildParagraph(
                  '회사는 위탁계약 체결 시 개인정보 보호 관련 법규의 준수, 개인정보에 관한 비밀 유지, 제3자 제공 금지 및 사고 시의 책임 부담 등을 명확히 규정하고, 해당 내용을 서면 또는 전자적으로 보관하고 있습니다.',
                ),
              ],
            ),
            buildSection(
              title: '제6조 (사용자의 권리·의무 및 그 행사방법)',
              children: [
                buildParagraph(
                  '사용자는 언제든지 등록되어 있는 자신의 개인정보를 조회하거나 수정할 수 있으며 가입 해지(동의 철회)를 요청할 수도 있습니다. 개인정보의 조회, 수정, 삭제, 처리정지 등의 권리 행사는 회사의 고객센터를 통해 본인 확인 절차를 거친 후 가능합니다.',
                ),
              ],
            ),
            buildSection(
              title: '제7조 (개인정보 자동 수집 장치의 설치·운영 및 그 거부에 관한 사항)',
              children: [
                buildParagraph(
                  '회사는 개인화되고 맞춤화된 서비스를 제공하기 위해서 이용자의 정보를 저장하고 수시로 불러오는 ‘쿠키(cookie)’를 사용합니다. 사용자는 쿠키 설치에 대한 선택권을 가지고 있으며, 웹브라우저에서 옵션을 설정함으로써 모든 쿠키를 허용하거나, 쿠키가 저장될 때마다 확인을 거치거나, 아니면 모든 쿠키의 저장을 거부할 수도 있습니다.',
                ),
              ],
            ),
            buildSection(
              title: '제8조 (개인정보의 기술적·관리적 보호 대책)',
              children: [
                buildParagraph(
                  '회사는 사용자의 개인정보를 처리함에 있어 개인정보가 분실, 도난, 유출, 변조 또는 훼손되지 않도록 안전성 확보를 위하여 다음과 같은 기술적·관리적 대책을 강구하고 있습니다.',
                ),
                buildListItem('개인정보 암호화: 비밀번호 등 주요 개인정보는 암호화하여 저장 및 관리합니다.'),
                buildListItem(
                  '해킹 등에 대비한 기술적 대책: 해킹이나 컴퓨터 바이러스 등에 의한 개인정보 유출 및 훼손을 막기 위하여 보안프로그램을 설치하고 주기적인 갱신·점검을 하며 외부로부터 접근이 통제된 구역에 시스템을 설치하고 기술적/물리적으로 감시 및 차단하고 있습니다.',
                ),
                buildListItem(
                  '개인정보 처리 직원의 최소화 및 교육: 개인정보를 처리하는 직원을 최소화하고, 관련 교육을 통해 개인정보 보호의 중요성을 인지시키고 있습니다.',
                ),
              ],
            ),
            buildSection(
              title: '제9조 (개인정보 보호책임자 및 담당부서 안내)',
              children: [
                buildParagraph(
                  '회사는 개인정보 처리에 관한 업무를 총괄해서 책임지고, 개인정보 처리와 관련한 정보주체의 불만 처리 및 피해구제 등을 위하여 아래와 같이 개인정보 보호책임자를 지정하고 있습니다.',
                ),
                buildListItem('개인정보 보호책임자: OOO'),
                buildListItem('담당부서: 개인정보보호팀'),
                buildListItem('연락처: contact@samantha.app'),
              ],
            ),
            buildSection(
              title: '제10조 (고지의 의무)',
              children: [
                buildParagraph(
                  '현 개인정보 처리방침 내용 추가, 삭제 및 수정이 있을 시에는 개정 최소 7일 전부터 서비스 내 ‘공지사항’을 통해 고지할 것입니다.',
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
