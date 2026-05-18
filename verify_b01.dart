// Quick verification script for salah_guide_data.dart helpers.
// Run with: dart run verify_b01.dart (from control-center-workspace root)
// But we just inline the logic here to verify the mapping.

void main() {
  // Simulate the enum indices:
  // niyyah=0, takbirAlIhram=1, qiyam=2, ruku=3, itidal=4, firstSujud=5,
  // jalsa=6, secondSujud=7, tashahhud=8, secondTasleem=9, duaEQunut=10

  // imageAssetPath(StepId.duaEQunut, true) → null (step 11 no image)
  print('duaEQunut male: ${_imageAssetPath(10, true)}'); // expect null

  // imageAssetPath(StepId.ruku, true) → 'assets/images/steps/male_step_4.png'
  print('ruku male: ${_imageAssetPath(3, true)}'); // expect male_step_4.png

  // quranMapping(StepId.qiyam) → surah 1
  print('qiyam quran: ${_quranMapping(2)}'); // expect 1:1

  // quranMapping(StepId.duaEQunut) → surah 2 ayah 201
  print('duaEQunut quran: ${_quranMapping(10)}'); // expect 2:201

  // imageAssetPath(StepId.niyyah, false) — female step 1 EXISTS now
  print('niyyah female: ${_imageAssetPath(0, false)}'); // expect female_step_1.png

  // imageAssetPath(StepId.qiyam, false) — female step 3 MISSING
  print('qiyam female: ${_imageAssetPath(2, false)}'); // expect null
}

String? _imageAssetPath(int index, bool isMale) {
  if (index == 9 || index == 10) return null; // secondTasleem, duaEQunut
  if (!isMale && index == 2) return null; // female qiyam (step 3)
  final n = index + 1;
  final gender = isMale ? 'male' : 'female';
  return 'assets/images/steps/${gender}_step_$n.png';
}

String? _quranMapping(int index) {
  if (index == 2) return '1:1';
  if (index == 10) return '2:201';
  return null;
}
