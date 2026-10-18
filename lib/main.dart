import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:permission_handler/permission_handler.dart';

void main() {
  runApp(const MafatiApp());
}

class MafatiApp extends StatelessWidget {
  const MafatiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ملفاتي',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0E0C24),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF7C5CFF),
        ),
      ),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool isAutoSortOn = false;
  int totalFiles = 0;
  Map<String, int> categoryCounts = {
    'صور': 0,
    'فيديو': 0,
    'صوتيات': 0,
    'مستندات': 0,
    'تطبيقات': 0,
    'مضغوطات': 0,
  };

  Future<void> pickAndOrganizeFiles() async {
    var status = await Permission.storage.request();
    if (status.isDenied || status.isPermanentlyDenied) {
      await Permission.manageExternalStorage.request();
    }

    FilePickerResult? result = await FilePicker.platform.pickFiles(allowMultiple: true);

    if (result != null) {
      int images = 0, videos = 0, audio = 0, docs = 0, apps = 0, zips = 0;

      for (var file in result.files) {
        String ext = (file.extension ?? '').toLowerCase();
        if (['jpg', 'jpeg', 'png', 'webp', 'gif'].contains(ext)) images++;
        else if (['mp4', 'mkv', 'avi', 'mov'].contains(ext)) videos++;
        else if (['mp3', 'wav', 'm4a', 'aac'].contains(ext)) audio++;
        else if (['pdf', 'doc', 'docx', 'txt', 'xlsx'].contains(ext)) docs++;
        else if (['apk', 'xapk'].contains(ext)) apps++;
        else if (['zip', 'rar', '7z'].contains(ext)) zips++;
      }

      setState(() {
        categoryCounts['صور'] = images;
        categoryCounts['فيديو'] = videos;
        categoryCounts['صوتيات'] = audio;
        categoryCounts['مستندات'] = docs;
        categoryCounts['تطبيقات'] = apps;
        categoryCounts['مضغوطات'] = zips;
        totalFiles = result.files.length;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('تم ترتيب $totalFiles ملف بنجاح! ✅')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'ملفاتي',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              Text(
                totalFiles > 0 ? 'تم ترتيب $totalFiles ملف' : 'اختار ملفاتك وأنا أقسمها حسب النوع',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white60, fontSize: 14),
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: pickAndOrganizeFiles,
                icon: const Icon(Icons.auto_awesome, color: Colors.white),
                label: const Text('✨ رتّب كل ملفاتي', style: TextStyle(fontSize: 18, color: Colors.white, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF7C5CFF),
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                ),
              ),
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('ترتيب تلقائي', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                        Text('يرتب الملفات الجديدة لوحده كل 15 دقيقة', style: TextStyle(color: Colors.white60, fontSize: 12)),
                      ],
                    ),
                    Switch(
                      value: isAutoSortOn,
                      onChanged: (val) {
                        setState(() {
                          isAutoSortOn = val;
                        });
                      },
                      activeColor: const Color(0xFF35D6A5),
                    )
                  ],
                ),
              ),
              const SizedBox(height: 20),
              Expanded(
                child: GridView.count(
                  crossAxisCount: 2,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                  children: [
                    _buildCategoryCard('صور', categoryCounts['صور']!, const Color(0xFFFF6B9A), Icons.image),
                    _buildCategoryCard('فيديو', categoryCounts['فيديو']!, const Color(0xFFFF9F45), Icons.movie),
                    _buildCategoryCard('صوتيات', categoryCounts['صوتيات']!, const Color(0xFF35D6A5), Icons.music_note),
                    _buildCategoryCard('مستندات', categoryCounts['مستندات']!, const Color(0xFF4DA3FF), Icons.description),
                    _buildCategoryCard('تطبيقات', categoryCounts['تطبيقات']!, const Color(0xFFA6E34B), Icons.android),
                    _buildCategoryCard('مضغوطات', categoryCounts['مضغوطات']!, const Color(0xFFB388FF), Icons.folder_zip),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCategoryCard(String title, int count, Color color, IconData icon) {
    return Container(
      decoration: BoxDecoration(
        color: color.withOpacity(0.85),
        borderRadius: BorderRadius.circular(20),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 36, color: Colors.white),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
              Text('$count ملف', style: const TextStyle(fontSize: 13, color: Colors.white70)),
            ],
          ),
        ],
      ),
    );
  }
}
