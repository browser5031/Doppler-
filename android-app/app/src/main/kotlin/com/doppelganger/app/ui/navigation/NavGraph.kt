package com.doppelganger.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.doppelganger.app.data.repository.DoppelgangerRepository
import com.doppelganger.app.ui.admin.AdminScreen
import com.doppelganger.app.ui.auth.AuthScreen
import com.doppelganger.app.ui.favorites.FavoritesScreen
import com.doppelganger.app.ui.home.HomeScreen

sealed class Screen(val route: String) {
    object Auth : Screen("auth")
    object Home : Screen("home")
    object Favorites : Screen("favorites")
    object Admin : Screen("admin")
}

@Composable
fun NavGraph(
    repository: DoppelgangerRepository = hiltViewModel<AuthViewModel>().repository
) {
    val navController = rememberNavController()
    val token by repository.getToken().collectAsState(initial = null)
    
    val startDestination = if (token != null) Screen.Home.route else Screen.Auth.route
    
    NavHost(
        navController = navController,
        startDestination = startDestination
    ) {
        composable(Screen.Auth.route) {
            AuthScreen(
                onNavigateToHome = {
                    navController.navigate(Screen.Home.route) {
                        popUpTo(Screen.Auth.route) { inclusive = true }
                    }
                }
            )
        }
        
        composable(Screen.Home.route) {
            HomeScreen(
                onNavigateToFavorites = {
                    navController.navigate(Screen.Favorites.route)
                },
                onNavigateToAdmin = {
                    navController.navigate(Screen.Admin.route)
                }
            )
        }
        
        composable(Screen.Favorites.route) {
            FavoritesScreen(
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }
        
        composable(Screen.Admin.route) {
            AdminScreen(
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }
    }
}
