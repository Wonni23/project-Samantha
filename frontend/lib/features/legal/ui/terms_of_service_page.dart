import 'package:flutter/material.dart';

import 'package:frontend/common/widgets/header.dart';
import 'package:frontend/features/legal/ui/widgets/legal_page_helpers.dart';

class TermsOfServicePage extends StatelessWidget {
  const TermsOfServicePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const Header(title: '서비스 이용약관'),
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
              'Samantha 서비스에 오신 것을 환영합니다. 본 약관은 주식회사 Samantha(이하 ‘회사’)가 제공하는 모든 Samantha 관련 제반 서비스(이하 ‘서비스’)의 이용과 관련하여 회사와 회원 간의 권리, 의무 및 책임사항, 기타 필요한 사항을 규정함을 목적으로 합니다.',
            ),
            buildSection(
              title: '제1조 (용어의 정의)',
              children: [
                buildListItem(
                  "'회원'이라 함은 본 약관에 따라 회사와 이용계약을 체결하고 회사가 제공하는 서비스를 이용하는 고객을 말합니다.",
                ),
                buildListItem(
                  "'유료 서비스'라 함은 회사가 유료로 제공하는 각종 디지털 콘텐츠 및 제반 서비스를 의미합니다.",
                ),
                buildListItem(
                  "'게시물'이라 함은 회원이 서비스에 게시한 문자, 음성, 이미지, 동영상 등의 정보 형태의 글, 사진, 동영상 및 각종 파일과 링크 등을 의미합니다.",
                ),
              ],
            ),
            buildSection(
              title: '제2조 (약관의 게시와 개정)',
              children: [
                buildParagraph(
                  '1. 회사는 본 약관의 내용을 회원이 쉽게 알 수 있도록 서비스 초기 화면 또는 연결화면을 통해 공지합니다.',
                ),
                buildParagraph(
                  '2. 회사는 「약관의 규제에 관한 법률」, 「정보통신망 이용촉진 및 정보보호 등에 관한 법률」 등 관련법을 위배하지 않는 범위에서 본 약관을 개정할 수 있습니다.',
                ),
                buildParagraph(
                  '3. 회사가 약관을 개정할 경우에는 적용일자 및 개정사유를 명시하여 현행약관과 함께 제1항의 방식에 따라 그 개정약관의 적용일자 7일 전부터 적용일자 전일까지 공지합니다.',
                ),
              ],
            ),
            buildSection(
              title: '제3조 (회원가입 및 이용계약 체결)',
              children: [
                buildParagraph(
                  '1. 이용계약은 회원이 되고자 하는 자(이하 ‘가입신청자’)가 약관의 내용에 대하여 동의를 한 다음 회원가입신청을 하고 회사가 이러한 신청에 대하여 승낙함으로써 체결됩니다.',
                ),
                buildParagraph(
                  '2. 회사는 가입신청자의 신청에 대하여 서비스 이용을 승낙함을 원칙으로 합니다. 다만, 회사는 다음 각 호에 해당하는 신청에 대하여는 승낙을 하지 않거나 사후에 이용계약을 해지할 수 있습니다.',
                ),
                buildListItem('가입신청자가 이 약관에 의하여 이전에 회원자격을 상실한 적이 있는 경우'),
                buildListItem('실명이 아니거나 타인의 명의를 이용한 경우'),
                buildListItem('허위의 정보를 기재하거나, 회사가 제시하는 내용을 기재하지 않은 경우'),
                buildListItem('만 14세 미만 아동이 법정대리인의 동의를 얻지 아니한 경우'),
              ],
            ),
            buildSection(
              title: '제4조 (회사의 의무)',
              children: [
                buildParagraph(
                  '1. 회사는 관련 법령과 본 약관이 금지하거나 미풍양속에 반하는 행위를 하지 않으며, 계속적이고 안정적으로 서비스를 제공하기 위하여 최선을 다하여 노력합니다.',
                ),
                buildParagraph(
                  '2. 회사는 회원이 안전하게 서비스를 이용할 수 있도록 개인정보 보호를 위해 보안시스템을 갖추어야 하며 개인정보 처리방침을 공시하고 준수합니다.',
                ),
              ],
            ),
            buildSection(
              title: '제5조 (회원의 의무)',
              children: [
                buildParagraph('1. 회원은 다음 행위를 하여서는 안 됩니다.'),
                buildListItem('개인정보의 허위 내용 등록 또는 타인의 정보 도용'),
                buildListItem('회사가 게시한 정보의 변경'),
                buildListItem('회사와 기타 제3자의 저작권 등 지적재산권에 대한 침해'),
                buildListItem('회사와 기타 제3자의 명예를 손상시키거나 업무를 방해하는 행위'),
                buildListItem(
                  '외설 또는 폭력적인 메시지, 화상, 음성, 기타 공서양속에 반하는 정보를 서비스에 공개 또는 게시하는 행위',
                ),
                buildListItem(
                  '정상적인 서비스 이용이 아니라고 판단되는 다량의 정보 전송, 자동화된 수단을 통한 서비스 접근 등',
                ),
              ],
            ),
            buildSection(
              title: '제6조 (서비스의 제공 및 변경)',
              children: [
                buildParagraph(
                  '1. 회사는 회원에게 아래와 같은 서비스를 제공합니다.',
                ),
                buildListItem('AI 캐릭터와의 대화 서비스 (텍스트, 음성)'),
                buildListItem('개인 맞춤형 정보 제공 서비스'),
                buildListItem(
                  '기타 회사가 추가 개발하거나 다른 회사와의 제휴계약 등을 통해 회원에게 제공하는 일체의 서비스',
                ),
                buildParagraph(
                  '2. 회사는 상당한 이유가 있는 경우에 운영상, 기술상의 필요에 따라 제공하고 있는 전부 또는 일부 서비스를 변경할 수 있습니다.',
                ),
              ],
            ),
            buildSection(
              title: '제7조 (게시물의 저작권)',
              children: [
                buildParagraph(
                  '1. 회원이 서비스 내에 게시한 게시물의 저작권은 해당 게시물의 저작자에게 귀속됩니다.',
                ),
                buildParagraph(
                  '2. 회원이 서비스 내에 게시하는 게시물은 서비스 및 관련 프로모션 등에 노출될 수 있으며, 해당 노출을 위해 필요한 범위 내에서는 일부 수정, 복제, 편집되어 게시될 수 있습니다.',
                ),
              ],
            ),
            buildSection(
              title: '제8조 (유료 서비스)',
              children: [
                buildParagraph(
                  '1. 회사는 일부 서비스를 유료로 제공할 수 있으며, 유료 서비스의 이용 요금, 결제 방식 등은 해당 서비스에 명시된 바에 따릅니다.',
                ),
                buildParagraph(
                  '2. 회원이 유료 서비스를 이용하는 경우, 회사가 정한 결제수단을 통해 요금을 납부해야 합니다.',
                ),
                buildParagraph('3. 유료 서비스의 환불 규정은 「콘텐츠산업 진흥법」 등 관련 법령에 따릅니다.'),
              ],
            ),
            buildSection(
              title: '제9조 (서비스 이용의 제한 및 정지)',
              children: [
                buildParagraph(
                  '회사는 회원이 본 약관의 의무를 위반하거나 서비스의 정상적인 운영을 방해한 경우, 경고, 일시정지, 영구이용정지 등으로 서비스 이용을 단계적으로 제한할 수 있습니다.',
                ),
              ],
            ),
            buildSection(
              title: '제10조 (계약해제, 해지 등)',
              children: [
                buildParagraph(
                  '1. 회원은 언제든지 서비스 내 정보 관리 메뉴를 통하여 이용계약 해지 신청을 할 수 있으며, 회사는 관련법 등이 정하는 바에 따라 이를 즉시 처리하여야 합니다.',
                ),
                buildParagraph(
                  '2. 회원이 계약을 해지할 경우, 관련법 및 개인정보 처리방침에 따라 회사가 회원정보를 보유하는 경우를 제외하고는 해지 즉시 회원의 모든 데이터는 소멸됩니다.',
                ),
              ],
            ),
            buildSection(
              title: '제11조 (면책조항)',
              children: [
                buildParagraph(
                  '1. 회사는 천재지변 또는 이에 준하는 불가항력으로 인하여 서비스를 제공할 수 없는 경우에는 서비스 제공에 관한 책임이 면제됩니다.',
                ),
                buildParagraph(
                  '2. 회사는 회원의 귀책사유로 인한 서비스 이용의 장애에 대하여는 책임을 지지 않습니다.',
                ),
                buildParagraph(
                  '3. AI가 생성하는 정보는 완전성과 정확성을 보장하지 않으며, 회사는 해당 정보로 인해 발생하는 어떠한 결과에 대해서도 책임을 지지 않습니다. 중요한 결정은 전문가와 상의하시기 바랍니다.',
                ),
              ],
            ),
            buildSection(
              title: '제12조 (준거법 및 재판관할)',
              children: [
                buildParagraph(
                  '1. 회사와 회원 간에 제기된 소송은 대한민국법을 준거법으로 합니다.',
                ),
                buildParagraph(
                  '2. 회사와 회원 간 발생한 분쟁에 관한 소송은 민사소송법상의 관할법원에 제소합니다.',
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
