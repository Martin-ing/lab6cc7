#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <semaphore.h>
#include <time.h>
#include <unistd.h>
#include <string.h>

#define NUM_CARS 10
#define NUM_SPOTS 3
#define NAME_FILE "parking_log.txt"

sem_t parking_semaphore;
pthread_mutex_t log_mutex;
pthread_mutex_t stats_mutex;

int cars_parked = 0;
double wait_time = 0.0;

FILE *log_f;

void log_event(const char *message) {
    time_t now = time(NULL);
    char time_buf[64];
    struct tm *tm_info = localtime(&now);
    strftime(time_buf, sizeof(time_buf), "%a %b %d %H:%M:%S %Y", tm_info);

    pthread_mutex_lock(&log_mutex);
    printf("[%s] %s\n", time_buf, message);
    fflush(stdout);
    if (log_f) {
        fprintf(log_f, "[%s] %s\n", time_buf, message);
        fflush(log_f);
    }
    pthread_mutex_unlock(&log_mutex);
}

void *car_thread(void *arg) {
    int car_id = *(int *)arg;
    free(arg);
    char msg[128];

    snprintf(msg, sizeof(msg), "Car %d: Arrived at parking lot", car_id);
    log_event(msg);

    time_t arrive_time = time(NULL);

    sem_wait(&parking_semaphore);
    
    time_t park_time = time(NULL);

    double wait_seconds = park_time - arrive_time;

    sprintf(msg, "Car %d: Parked successfully (waited %.2f seconds)", car_id, wait_seconds);
    log_event(msg);

    pthread_mutex_lock(&stats_mutex);
    cars_parked++;
    wait_time += wait_seconds;
    pthread_mutex_unlock(&stats_mutex);

    int park_duration = (rand() % 5) + 1;
    sleep(park_duration);

    sprintf(msg, "Car %d: Leaving parking lot", car_id);
    log_event(msg);

    sem_post(&parking_semaphore);

    return NULL;
}

int main(void) {
    srand(time(NULL));

    log_f = fopen(NAME_FILE, "w");
    if (!log_f) {
        perror("fopen");
        return 1;
    }
    printf("asdasd");
    sem_init(&parking_semaphore, 0, NUM_SPOTS);
    pthread_mutex_init(&log_mutex, NULL);
    pthread_mutex_init(&stats_mutex, NULL);

    pthread_t threads[NUM_CARS];

    for (int i = 0; i < NUM_CARS; i++) {
        int *id = malloc(sizeof(int));
        *id = i;
        pthread_create(&threads[i], NULL, car_thread, id);
    }

    for (int i = 0; i < NUM_CARS; i++) {
        pthread_join(threads[i], NULL);
    }

    printf("\nTotal cars parked: %d\n", cars_parked);
    printf("Average wait time: %.2f seconds\n", wait_time / cars_parked);

    if (log_f) {
        fprintf(log_f, "\nTotal cars parked: %d\n", cars_parked);
        fprintf(log_f, "Average wait time: %.2f seconds\n", wait_time / cars_parked);
        fclose(log_f);
    }

    sem_destroy(&parking_semaphore);
    pthread_mutex_destroy(&log_mutex);
    pthread_mutex_destroy(&stats_mutex);

    return 0;
}
