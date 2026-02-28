package com.doppelganger.app.ui.favorites

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.doppelganger.app.data.api.models.FaceMatch
import com.doppelganger.app.data.repository.DoppelgangerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class FavoritesViewModel @Inject constructor(
    private val repository: DoppelgangerRepository
) : ViewModel() {
    
    private val _uiState = MutableStateFlow<FavoritesUiState>(FavoritesUiState.Loading)
    val uiState: StateFlow<FavoritesUiState> = _uiState.asStateFlow()
    
    init {
        loadFavorites()
    }
    
    fun loadFavorites() {
        viewModelScope.launch {
            _uiState.value = FavoritesUiState.Loading
            repository.getFavorites()
                .onSuccess { favorites ->
                    _uiState.value = if (favorites.isEmpty()) {
                        FavoritesUiState.Empty
                    } else {
                        FavoritesUiState.Success(favorites)
                    }
                }
                .onFailure { error ->
                    _uiState.value = FavoritesUiState.Error(error.message ?: "Failed to load favorites")
                }
        }
    }
    
    fun removeFavorite(faceId: String) {
        viewModelScope.launch {
            repository.removeFavorite(faceId)
                .onSuccess {
                    loadFavorites()
                }
        }
    }
}

sealed class FavoritesUiState {
    object Loading : FavoritesUiState()
    object Empty : FavoritesUiState()
    data class Success(val favorites: List<FaceMatch>) : FavoritesUiState()
    data class Error(val message: String) : FavoritesUiState()
}