package com.doppelganger.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DarkColorScheme = darkColorScheme(
    primary = NeonGreen,
    onPrimary = Color(0xFF000000),
    primaryContainer = NeonGreenDark,
    onPrimaryContainer = Color(0xFFFFFFFF),
    
    secondary = Purple,
    onSecondary = Color(0xFFFFFFFF),
    secondaryContainer = PurpleDark,
    onSecondaryContainer = Color(0xFFFFFFFF),
    
    tertiary = WarningYellow,
    onTertiary = Color(0xFF000000),
    
    error = ErrorRed,
    onError = Color(0xFFFFFFFF),
    
    background = DarkBackground,
    onBackground = TextPrimary,
    
    surface = DarkSurface,
    onSurface = TextPrimary,
    
    surfaceVariant = DarkCard,
    onSurfaceVariant = TextSecondary,
    
    outline = TextTertiary,
    outlineVariant = Color(0xFF3F3F46)
)

@Composable
fun DoppelgangerTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = DarkColorScheme
    
    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}