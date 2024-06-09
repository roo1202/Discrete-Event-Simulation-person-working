import numpy as np
import scipy.stats as st
import simpy
import copy
import pandas as pd

# Parametros de la simulacion
RANDOM_SEED = 42
TASK_MEAN = 24.0
INTERRUPTION_MEAN = 10.0
INTERRUPTION_DUR = 3.0
BREAK_MEAN = 6.0

np.random.seed(RANDOM_SEED)


def time_per_task():
    return st.expon.rvs(size=1, scale=TASK_MEAN)[0]

def time_to_interrupt(enabled=1):
    if enabled:
        return st.expon.rvs(size=1, scale=INTERRUPTION_MEAN)[0]
    return 10000

def time_to_break(fixed=0):
    if fixed:
        return fixed
    return time_per_task()

def break_duration(fixed=0):
    if fixed:
        return fixed
    return st.expon.rvs(size=1, scale=BREAK_MEAN)[0]

def interruption_duration(enabled=1):
    if enabled:
        return st.expon.rvs(size=1, scale=INTERRUPTION_DUR)[0]
    return 0


class Person:
    def __init__(self,env,state, b_time, b_duration, concentration=2, interr=True, verbose=False, minconcentr=0.4):
        # Simpy Config
        self.state = state
        self.env = env
        self.person = simpy.PreemptiveResource(env,capacity=1)

        # Productivity
        self.c = concentration

        #Variables
        self.completed_tasks = 0
        self.breaks = 0
        self.interrupts = 0
        self.task_duration_sum = 0
        self.break_duration_sum = 0
        self.interruption_duration_sum = 0

        # Metodología
        self.b_time, self.b_duration = b_time, b_duration
        self.min_c = minconcentr
        self.interrupting_enabled = interr
        self.verbose = verbose
        
        #Procesos
        self.process_working = env.process(self.working())
        env.process(self.interrupting())
        self.process_break = env.process(self.take_break())

        #canatidad para el calculo de probabilidades para el modelo de cadenas de markov,
        self.work_to_work = 0
        self.work_to_break = 0
        self.work_to_interrupt = 0

        self.break_to_work = 0
        self.break_to_interrupt = 0

        self.interrupt_to_work = 0
        self.interrupt_to_break = 0

    def printv(self, s):
        if self.verbose:
            print(s)

    def working(self):
        while True:
            time = time_per_task()
            t_duration = time
            
            it = ""
            while time:    
                start = self.env.now
                try:
                    self.printv(f'Minuto {self.env.now} | {it}iniciando tarea {self.completed_tasks+1} | queda por trabajar {time} min')
                    self.state = 'W'

                    yield self.env.timeout(time)
                    self.task_duration_sum += time/max(self.c, self.min_c)
                    self.c = max(self.min_c , self.c-time/100)
                    time = 0
                    self.state = 'S'
                    self.work_to_work += 1

                except simpy.Interrupt:
                    time = max(0, time - (self.env.now - start)/max(self.c, self.min_c))
                    self.c = max(self.min_c, self.c - (self.env.now - start)/100)

                    if self.state == 'I':
                        interruption_time = interruption_duration()
                        self.printv(f'Minuto {self.env.now} | trabajo interrumpido por {interruption_time} | quedando por completar unos {time} min de tarea')
                        
                        yield self.env.timeout(interruption_time)
                        self.printv(f'Minuto {self.env.now} | interrupción terminada')
                        self.interruption_duration_sum += interruption_time
                        self.interrupts += 1
                        self.state = 'W'
                        self.work_to_interrupt += 1
                        self.interrupt_to_work += 1
                        
                    elif self.state == 'D': 
                        break_time = break_duration(self.b_duration)
                        break_t = break_time
                        start_break = self.env.now
                        self.printv(f'Minuto {self.env.now} | descanso por {break_time} min | quedando por completar unos {time} min de tarea')

                        while break_time:
                            try:
                                yield self.env.timeout(break_time)
                                self.break_duration_sum += break_time
                                self.c = min(2 , self.c + break_time/30)
                                
                                break_time = 0
                                self.work_to_break += 1
                                self.break_to_work += 1
                                #self.state = 'W'

                            except:
                                break_time = max(0 , break_time - self.env.now + start_break)
                                self.c = min(2, self.c + (self.env.now - start_break)/30)
                                
                                interruption_time = interruption_duration()
                                self.printv(f'Minuto {self.env.now} | descanso interrumpido por {interruption_time} min')
                                yield self.env.timeout(interruption_time)
                                self.printv(f'Minuto {self.env.now} | interrupción terminada')
                                self.interruption_duration_sum += interruption_time
                                self.interrupts += 1
                                # yield self.env.timeout(break_time)
                                self.state = 'D'
                                self.break_to_interrupt+=1
                                self.interrupt_to_break+=1

                        self.breaks += 1
                        # self.break_duration_sum += break_t
                        self.printv(f'Minuto {self.env.now} | descanso completado en el minuto {self.env.now}' )
                                
                
                    # yield self.env.timeout(time)
                    # time = 0
                    # self.state = 'S'            

                it='re'    
                
            self.completed_tasks += 1
            # self.task_duration_sum += t_duration
            self.printv(f'Minuto {self.env.now} | tarea numero {self.completed_tasks} completada')

    def take_break(self):
        dur = 0.0
        while True:
            time = time_to_break(self.b_time + dur)
            dur = self.b_duration
            yield self.env.timeout(time)
           
            with self.person.request(priority=1) as request:
                yield request
                    
                if self.state == 'W' and self.process_working.is_alive:
                    self.state = 'D'
                    self.process_working.interrupt()
                # elif self.state == 'I':
                #     print('no puedes descansar por interrupcion', self.env.now)
                

    def interrupting(self):
        while True:
            time = time_to_interrupt(self.interrupting_enabled)
            # print('solicitando proxima interrupcion en ', self.env.now, ' para dentro de :', time)
            yield self.env.timeout(time)
            
            with self.person.request(priority=0) as request:
                yield request
                # print('se obtuvo la interrupcion (el recurso) en el minuto', self.env.now)
                if (self.state == 'W' or self.state == 'D') and self.process_working.is_alive:
                    self.state = 'I'
                    self.process_working.interrupt()

                else:
                    self.printv(f'no se puede interrumpir en el minuto {self.env.now}')
            

def simulate(n, time, b_time=0, b_duration=0, interruptions=True, verbose=False, likelihood=False, MSE=[5,5,10,10,30,30,30,30]):
    df = pd.DataFrame({})

    i=0
    invalid = likelihood
    while invalid or i < n:
        env = simpy.Environment()
        person = Person(env,'S', b_time, b_duration,interr= interruptions)
        env.run(until=time)
        env.event().succeed()
        env.event().succeed()
        env.event().succeed()
        # Data Collecting
        row = pd.DataFrame(
            {  
                "break_duration": [b_duration], 
                "break_timestamp": [b_time],
                "interruptions": [copy.copy(person.interrupts)],
                "completed_tasks": [copy.copy(person.completed_tasks)],
                "breaks": [copy.copy(person.breaks)],
                "working_time": [copy.copy(person.task_duration_sum)],
                "break_time": [copy.copy(person.break_duration_sum)],
                "interruption_time": [copy.copy(person.interruption_duration_sum)],
            }
        )
        df = pd.concat([df,row])

        # To verify stopping criteria
        if likelihood:
            est_std = df.std()
            # print(len(est_std[est_std/np.sqrt(i+1) < MSE]))
            invalid = len(est_std[est_std/np.sqrt(i+1) < MSE]) < 8
        

        # If the simulation verbosity is true the print the outcomes
        if verbose:
            print("Descanso: ",person.breaks)
            print("Tareas Completadas: ",person.completed_tasks)
            print("Duración Media de tareas: ",person.task_duration_sum/person.completed_tasks)
            print("Interrupciónes: ",person.interrupts)

        i+=1
        
        
    return df
