/**
 * Error recovery and retry logic for API calls and streaming operations.
 * Provides exponential backoff, timeout handling, and graceful fallback mechanisms.
 */

/**
 * Configuration for retry behavior
 */
export interface RetryConfig {
  maxRetries: number;
  initialDelayMs: number;
  maxDelayMs: number;
  backoffMultiplier: number;
  timeoutMs: number;
}

/**
 * Default retry configuration
 */
export const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  initialDelayMs: 1000,
  maxDelayMs: 10000,
  backoffMultiplier: 2,
  timeoutMs: 30000,
};

/**
 * Result of a retry operation
 */
export interface RetryResult<T> {
  success: boolean;
  data?: T;
  error?: Error;
  attempts: number;
}

/**
 * Exponential backoff delay calculator
 */
export function calculateBackoffDelay(
  attempt: number,
  config: RetryConfig
): number {
  const delay = config.initialDelayMs * Math.pow(config.backoffMultiplier, attempt);
  return Math.min(delay, config.maxDelayMs);
}

/**
 * Retry a promise-returning function with exponential backoff
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  config: Partial<RetryConfig> = {}
): Promise<RetryResult<T>> {
  const finalConfig = { ...DEFAULT_RETRY_CONFIG, ...config };
  let lastError: Error | undefined;

  for (let attempt = 0; attempt < finalConfig.maxRetries; attempt++) {
    try {
      const promise = fn();
      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(
          () => reject(new Error("Operation timeout")),
          finalConfig.timeoutMs
        )
      );

      const data = await Promise.race([promise, timeoutPromise]);
      return { success: true, data, attempts: attempt + 1 };
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      if (attempt < finalConfig.maxRetries - 1) {
        const delay = calculateBackoffDelay(attempt, finalConfig);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  return {
    success: false,
    error: lastError || new Error("Unknown error"),
    attempts: finalConfig.maxRetries,
  };
}

/**
 * Retry streaming operations (like SSE)
 */
export async function retryStreamWithBackoff(
  fn: () => ReadableStream<string>,
  config: Partial<RetryConfig> = {}
): Promise<RetryResult<ReadableStream<string>>> {
  const finalConfig = { ...DEFAULT_RETRY_CONFIG, ...config };
  let lastError: Error | undefined;

  for (let attempt = 0; attempt < finalConfig.maxRetries; attempt++) {
    try {
      const stream = fn();
      // Test if stream is readable
      const reader = stream.getReader();
      await reader.read(); // Attempt to read first chunk
      reader.releaseLock();

      // Stream is valid, return a fresh stream
      return { success: true, data: fn(), attempts: attempt + 1 };
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      if (attempt < finalConfig.maxRetries - 1) {
        const delay = calculateBackoffDelay(attempt, finalConfig);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  return {
    success: false,
    error: lastError || new Error("Stream initialization failed"),
    attempts: finalConfig.maxRetries,
  };
}

/**
 * Parse API error response and extract user-friendly message
 */
export function parseApiError(error: unknown): string {
  if (error instanceof Response) {
    if (error.status === 408) return "Request timeout. Please try again.";
    if (error.status === 429) return "Too many requests. Please wait a moment.";
    if (error.status === 503) return "Service temporarily unavailable. Please try again later.";
    if (error.status >= 500) return "Server error. Please try again later.";
    if (error.status >= 400) return "Request failed. Please check your input.";
  }

  if (error instanceof Error) {
    if (error.message.includes("timeout")) return "Request timeout. Please try again.";
    if (error.message.includes("network")) return "Network error. Please check your connection.";
    return error.message;
  }

  return "An unexpected error occurred. Please try again.";
}

/**
 * Check if error is retryable
 */
export function isRetryableError(error: unknown): boolean {
  if (error instanceof Response) {
    // Retryable status codes
    return [408, 429, 500, 502, 503, 504].includes(error.status);
  }

  if (error instanceof Error) {
    return (
      error.message.includes("timeout") ||
      error.message.includes("network") ||
      error.message.includes("Connection")
    );
  }

  return false;
}
