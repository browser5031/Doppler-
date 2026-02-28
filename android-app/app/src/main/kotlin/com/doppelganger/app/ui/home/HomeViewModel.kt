package com.doppelganger.app.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.doppelganger.app.data.api.models.CompareResponse
import com.doppelganger.app.data.repository.DoppelgangerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.File
import javax.inject.Inject

@HiltViewModel
class HomeViewModel @Inject constructor(
    val repository: DoppelgangerRepository
) : ViewModel() {
    
    private val _uiState = MutableStateFlow<HomeUiState>(HomeUiState.Idle)
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()
    
    fun uploadImage(imageFile: File) {
        viewModelScope.launch {
            _uiState.value = HomeUiState.Loading
            repository.compareImage(imageFile)
                .onSuccess { response ->
                    _uiState.value = HomeUiState.Success(response)
                }
                .onFailure { error ->
                    _uiState.value = HomeUiState.Error(error.message ?: "Failed to analyze image")
                }
        }
    }
    
    fun resetState() {
        _uiState.value = HomeUiState.Idle
    }
}

sealed class HomeUiState {
    object Idle : HomeUiState()
    object Loading : HomeUiState()
    data class Success(val response: CompareResponse) : HomeUiState()
    data class Error(val message: String) : HomeUiState()
}