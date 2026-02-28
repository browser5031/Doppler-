package com.doppelganger.app.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.doppelganger.app.data.repository.DoppelgangerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val repository: DoppelgangerRepository
) : ViewModel() {
    
    private val _uiState = MutableStateFlow<AuthUiState>(AuthUiState.Idle)
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()
    
    fun login(username: String, password: String) {
        if (username.isBlank() || password.isBlank()) {
            _uiState.value = AuthUiState.Error("Please fill all fields")
            return
        }
        
        viewModelScope.launch {
            _uiState.value = AuthUiState.Loading
            repository.login(username, password)
                .onSuccess {
                    _uiState.value = AuthUiState.Success
                }
                .onFailure { error ->
                    _uiState.value = AuthUiState.Error(error.message ?: "Login failed")
                }
        }
    }
    
    fun register(username: String, password: String, email: String) {
        if (username.isBlank() || password.isBlank()) {
            _uiState.value = AuthUiState.Error("Please fill all required fields")
            return
        }
        
        if (password.length < 6) {
            _uiState.value = AuthUiState.Error("Password must be at least 6 characters")
            return
        }
        
        viewModelScope.launch {
            _uiState.value = AuthUiState.Loading
            repository.register(username, password, email.ifBlank { null })
                .onSuccess {
                    _uiState.value = AuthUiState.Success
                }
                .onFailure { error ->
                    _uiState.value = AuthUiState.Error(error.message ?: "Registration failed")
                }
        }
    }
    
    fun resetState() {
        _uiState.value = AuthUiState.Idle
    }
}

sealed class AuthUiState {
    object Idle : AuthUiState()
    object Loading : AuthUiState()
    object Success : AuthUiState()
    data class Error(val message: String) : AuthUiState()
}