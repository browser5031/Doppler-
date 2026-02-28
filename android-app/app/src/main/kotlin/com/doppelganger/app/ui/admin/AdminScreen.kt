package com.doppelganger.app.ui.admin

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdminScreen(
    onNavigateBack: () -> Unit,
    viewModel: AdminViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val actionState by viewModel.actionState.collectAsState()
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Admin Panel") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, "Back")
                    }
                }
            )
        }
    ) { padding ->
        when (val state = uiState) {
            is AdminUiState.Loading -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
            }
            is AdminUiState.Success -> {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding)
                        .padding(16.dp)
                ) {
                    Text(
                        text = "Scraper Statistics",
                        style = MaterialTheme.typography.headlineSmall
                    )
                    
                    Spacer(modifier = Modifier.height(16.dp))
                    
                    StatCard("Total Faces", state.status.totalFaces.toString())
                    StatCard("Total Yearbooks", state.status.totalYearbooks.toString())
                    StatCard("Processing", state.status.processing.toString())
                    StatCard("Completed", state.status.completed.toString())
                    StatCard("Queued", state.status.queued.toString())
                    if (state.status.failed > 0) {
                        StatCard("Failed", state.status.failed.toString())
                    }
                    
                    Spacer(modifier = Modifier.height(24.dp))
                    
                    Button(
                        onClick = { viewModel.autoDiscover(100) },
                        modifier = Modifier.fillMaxWidth(),
                        enabled = actionState !is ActionState.Loading
                    ) {
                        if (actionState is ActionState.Loading) {
                            CircularProgressIndicator(modifier = Modifier.size(24.dp))
                        } else {
                            Text("Auto-Discover & Scrape (100)")
                        }
                    }
                    
                    when (val action = actionState) {
                        is ActionState.Success -> {
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(
                                text = action.message,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }
                        is ActionState.Error -> {
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(
                                text = action.message,
                                color = MaterialTheme.colorScheme.error
                            )
                        }
                        else -> {}
                    }
                }
            }
            is AdminUiState.Error -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Text(state.message)
                }
            }
        }
    }
}

@Composable
fun StatCard(label: String, value: String) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(label)
            Text(
                text = value,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}