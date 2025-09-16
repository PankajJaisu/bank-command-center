/**
 * Sync Events - Cross-page notification system for sync completion
 */

export type SyncEventType = 'sync_completed' | 'sync_started';

export interface SyncEvent {
  type: SyncEventType;
  jobId: number;
  timestamp: Date;
  totalFiles?: number;
  successfulFiles?: number;
}

class SyncEventManager {
  private listeners: Map<SyncEventType, Array<(event: SyncEvent) => void>> = new Map();

  /**
   * Subscribe to sync events
   */
  on(eventType: SyncEventType, callback: (event: SyncEvent) => void) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType)!.push(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = this.listeners.get(eventType);
      if (callbacks) {
        const index = callbacks.indexOf(callback);
        if (index > -1) {
          callbacks.splice(index, 1);
        }
      }
    };
  }

  /**
   * Emit sync event
   */
  emit(event: SyncEvent) {
    const callbacks = this.listeners.get(event.type);
    if (callbacks) {
      callbacks.forEach(callback => callback(event));
    }
  }

  /**
   * Notify that sync has completed
   */
  notifySyncCompleted(jobId: number, totalFiles: number, successfulFiles: number) {
    this.emit({
      type: 'sync_completed',
      jobId,
      totalFiles,
      successfulFiles,
      timestamp: new Date()
    });
  }

  /**
   * Notify that sync has started
   */
  notifySyncStarted(jobId: number) {
    this.emit({
      type: 'sync_started',
      jobId,
      timestamp: new Date()
    });
  }
}

// Global instance
export const syncEvents = new SyncEventManager();
