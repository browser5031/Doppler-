package com.doppelganger.app.ui.admin

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.doppelganger.app.data.api.models.ScraperStatus
import com.doppelganger.app.data.repository.DoppelgangerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AdminViewModel @Inject constructor(
    private val repository: DoppelgangerRepository
) : ViewModel() {
    
    private val _uiState = MutableStateFlow<AdminUiState>(AdminUiState.Loading)
    val uiState: StateFlow<AdminUiState> = _uiState.asStateFlow()
    
    private val _actionState = MutableStateFlow<ActionState>(ActionState.Idle)
    val actionState: StateFlow<ActionState> = _actionState.asStateFlow()
    
    init {
        loadStatus()
        startAutoRefresh()
    }
    
    private fun startAutoRefresh() {
        viewModelScope.launch {
            while (true) {
                delay(5000) // Refresh every 5 seconds
                loadStatus(silent = true)
            }
        }
    }
    
    fun loadStatus(silent: Boolean = false) {
        viewModelScope.launch {
            if (!silent) {
                _uiState.value = AdminUiState.Loading
            }
            repository.getScraperStatus()
                .onSuccess { status ->
                    _uiState.value = AdminUiState.Success(status)
                }
                .onFailure { error ->
                    _uiState.value = AdminUiState.Error(error.message ?: "Failed to load status")
                }
        }
    }
    
    fun autoDiscover(limit: Int = 100) {
        viewModelScope.launch {
            _actionState.value = ActionState.Loading("Starting auto-discovery...")
            repository.autoDiscover(limit)
                .onSuccess {
                    _actionState.value = ActionState.Success("Started scraping $limit yearbooks!")
                    loadStatus()
                    delay(2000)
                    _actionState.value = ActionState.Idle
                }
                .onFailure { error ->
                    _actionState.value = ActionState.Error(error.message ?: "Failed to start")
                    delay(2000)
                    _actionState.value = ActionState.Idle
                }
        }
    }
}

sealed class AdminUiState {
    object Loading : AdminUiState()
    data class Success(val status: ScraperStatus) : AdminUiState()
    data class Error(val message: String) : AdminUiState()
}

sealed class ActionState {
    object Idle : ActionState()
    data class Loading(val message: String) : ActionState()
    data class Success(val message: String) : ActionState()
    data class Error(val message: String) : ActionState()
}