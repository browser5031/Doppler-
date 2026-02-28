# Doppelgänger Android App

Native Android app for finding your doppelganger in yearbook photos!

## 📦 Download APK

### Option 1: GitHub Actions (Automatic Build)

1. Go to **Actions** tab in this GitHub repository
2. Click on the latest workflow run
3. Download `doppelganger-debug.apk` from Artifacts
4. Install on your Android phone

### Option 2: Build Locally (If you have Android Studio)

```bash
./gradlew assembleDebug
# APK will be in: app/build/outputs/apk/debug/app-debug.apk
```

## 🚀 Setup

### Configure Backend URL

Before building, set your backend URL:

1. Create `local.properties` file in root:
```properties
backend.url=https://your-app.preview.emergentagent.com
```

2. Or set as GitHub Secret:
   - Go to Settings → Secrets → Actions
   - Add secret: `BACKEND_URL` = `https://your-app-url.com`

## 📱 Features

- ✅ Login/Register with username & password
- ✅ Upload photo from gallery
- ✅ AI face comparison
- ✅ View top 50 similar matches
- ✅ Save favorites
- ✅ Admin panel to manage scraping
- ✅ Dark mode UI with neon green theme
- ✅ Material 3 Design

## 🛠️ Tech Stack

- **Language:** Kotlin
- **UI:** Jetpack Compose + Material 3
- **Architecture:** MVVM + Repository
- **Networking:** Retrofit + OkHttp
- **DI:** Hilt
- **Image Loading:** Coil
- **Storage:** DataStore

## 📸 Screenshots

[Add screenshots after building]

## 👤 User Guide

### First Time Setup

1. **Install APK** on your Android device
2. **Register** a new account
3. **Upload a photo** from gallery
4. **View matches** - see your top doppelgangers!

### Admin Features

1. Tap **Settings icon** (top right)
2. View scraping statistics
3. Tap **Auto-Discover** to scrape 100 new yearbooks
4. Monitor progress

## 🔧 Development

### Prerequisites

- Android Studio Hedgehog or later
- JDK 17+
- Minimum SDK 24 (Android 7.0)
- Target SDK 34 (Android 14)

### Build Commands

```bash
# Debug build
./gradlew assembleDebug

# Release build
./gradlew assembleRelease

# Install on connected device
./gradlew installDebug

# Run tests
./gradlew test
```

## 📡 API Endpoints

The app connects to these backend endpoints:

- `POST /api/mobile/auth/register` - Register user
- `POST /api/mobile/auth/login` - Login user
- `POST /api/mobile/compare` - Upload & compare face
- `GET /api/mobile/favorites` - Get saved favorites
- `GET /api/mobile/admin/scraper-status` - Admin stats
- `POST /api/mobile/admin/auto-discover` - Start scraping

## 🐛 Troubleshooting

### App crashes on launch
- Check if backend URL is correct in `local.properties`
- Ensure backend server is running

### Can't login
- Verify backend URL is accessible
- Check network connection
- Try registering a new account

### No matches found
- Database might be empty
- Use admin panel to start scraping
- Wait for faces to be collected

## 📝 License

MIT License

## 👏 Credits

Built with love for finding your twin! 👯‍♀️