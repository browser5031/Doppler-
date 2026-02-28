# Doppelganger Android App

Native Android app built with Kotlin and Jetpack Compose for finding your doppelganger in yearbook photos!

## Features

- 📸 **Camera Integration** - Take photo directly or choose from gallery
- 🔍 **Face Matching** - Upload your photo and find similar faces
- ❤️ **Save Favorites** - Save your best matches
- 👤 **Simple Auth** - Username/password authentication
- 👨‍💼 **Admin Panel** - Manage scraping from your phone
- 🌙 **Dark Mode** - Beautiful dark theme

## Tech Stack

- **Language:** Kotlin
- **UI:** Jetpack Compose + Material 3
- **Architecture:** MVVM with Repository pattern
- **Networking:** Retrofit + OkHttp
- **Image Loading:** Coil
- **Camera:** CameraX
- **Storage:** DataStore + Room (for offline favorites)
- **DI:** Hilt
- **Async:** Kotlin Coroutines + Flow

## Project Structure

```
app/
├── data/
│   ├── api/              # API interface & models
│   ├── repository/       # Data repositories
│   └── local/            # Room database
├── domain/
│   ├── model/            # Domain models
│   └── usecase/          # Business logic
├── ui/
│   ├── auth/             # Login/Register screens
│   ├── home/             # Main upload screen
│   ├── results/          # Match results
│   ├── favorites/        # Saved favorites
│   └── admin/            # Admin panel
└── util/                 # Utilities & extensions
```

## Setup

### Prerequisites
- Android Studio Hedgehog or later
- JDK 17+
- Minimum SDK: 24 (Android 7.0)
- Target SDK: 34 (Android 14)

### Configuration

1. Update `local.properties` with your backend URL:
```properties
backend.url=https://your-app.preview.emergentagent.com
```

2. Build the project:
```bash
./gradlew assembleDebug
```

3. Install on device/emulator:
```bash
./gradlew installDebug
```

## API Endpoints Used

### Authentication
- `POST /api/mobile/auth/register` - Register new user
- `POST /api/mobile/auth/login` - Login user

### Face Comparison
- `POST /api/mobile/compare` - Upload photo and find matches

### Favorites
- `POST /api/mobile/favorites` - Add to favorites
- `GET /api/mobile/favorites` - Get user favorites
- `DELETE /api/mobile/favorites/{id}` - Remove favorite

### Admin
- `GET /api/mobile/admin/scraper-status` - Get scraping status
- `POST /api/mobile/admin/start-scraping` - Start scraping yearbook
- `POST /api/mobile/admin/auto-discover` - Auto-discover and scrape

## Building APK

### Debug APK
```bash
./gradlew assembleDebug
# Output: app/build/outputs/apk/debug/app-debug.apk
```

### Release APK (requires signing)
```bash
./gradlew assembleRelease
# Output: app/build/outputs/apk/release/app-release.apk
```

## Screenshots

[Screenshots will be here once built]

## Permissions

```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
<uses-permission android:name="android.permission.INTERNET" />
```

## License

MIT License
