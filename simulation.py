
import random
import simpy
import scipy.stats as st

RANDOM_SEED = 42
TASK_MEAN = 10.0
TASK_SIGMA = 2.0

INTERRUPTION_MEAN = 30.0
INTERRUPTION_SIGMA = 3.0

BREAK_MEAN = 20.0
BREAK_SIGMA = 3.0


def time_per_task():
    return st.expon.rvs(size=1, scale=TASK_MEAN)[0]


def time_to_interrupt():
    t = random.normalvariate(4, 1)

    while t <= 0:
        t = random.normalvariate(4, 1)
    return t

def interrupt_duration():
    return 3


#Tiempo entre descansos
#A -> descansos autorregulados
#SL -> descansos sistematicos largos
#SC -> descansos sistematicos cortos

def A_time_to_break():
    return st.expon.rvs(size=1, scale=BREAK_MEAN)[0]

def SL_time_to_break():
    return 24

def SC_time_to_break():
    return 12

#Tiempo que toma el descanso, o duracion del descanso
def A_break_duration():
    t = random.normalvariate(14.67,13.71)

    while t <= 0:
        t = random.normalvariate(14.67, 13.71)
    return t

def SL_break_duration(time):
    return 6

def SC_break_duration(time):
    return 3


def update_energy(person,energy):
    person.energy += energy
    if person.energy < 0 :
        person.energy = 0
        return False
    else:
        person.energy = min(person.energy,100)
        return True




class Person:
    def __init__(self,env,state,time_to_break,break_duration):
        self.state = state
        self.env = env
        self.person = simpy.PreemptiveResource(env,capacity=1)
        self.completed_tasks = 0
        self.breaks = 0
        self.interrupts = 0
        self.energy = 100
        self.time_to_break = time_to_break
        self.break_duration = break_duration

        self.process_working = env.process(self.working())
        env.process(self.interrupting())
        self.process_break = env.process(self.take_break())

    def working(self):
        while True:
            time = time_per_task()
            print('duracion de la proxima tarea', time)
            
            while time:    
                start = self.env.now
                try:
                    print('empieza a trabajar en el ', self.env.now, 'queda por trabajar ', time)
                    self.state = 'W'
                    yield self.env.timeout(time)
                    print('se tiene una energia de ',self.energy)
                    if not update_energy(self, -5 * time):             # update
                        print('la energia ha llegado a 0')
                        #detener simulacion
                    print('la energia ahora es de ',self.energy)
                    time = 0
                    self.state = 'S'
                    print(f'tarea completada en el minuto ',self.env.now)
                except simpy.Interrupt:
                    time -= self.env.now - start
                    time = max(0, time)
                    print(f'trabajo interrumpido en el minuto ',self.env.now,', queda por completar unos ', time, ' minutos')
                    
                    if self.state == 'I':
                        
                        time_to_interruptt = 5
                        print('interrupcion en el', self.env.now, ' duracion:', time_to_interruptt)
                        yield self.env.timeout(time_to_interruptt)
                        print('interrupcion completada en el minuto', self.env.now)
                        self.interrupts += 1
                        #self.state = 'W'
                        
                    elif self.state == 'D': 
                        time_to_breakk = 7
                        start_break = self.env.now
                        while time_to_breakk:
                            try:
                                print('descansando en el', self.env.now, ' duracion:', time_to_breakk)
                                yield self.env.timeout(time_to_breakk)
                                print('descanso completada en el minuto', self.env.now)
                                self.breaks += 1
                                print('se tiene una energia de ',self.energy)
                                update_energy(self, time_to_breakk)             # update
                                print('la energia ahora es de ',self.energy)
                                time_to_breakk = 0
                                #self.state = 'W'
                            except:
                                time_to_interruptt = 5
                                print('interrupcion en el', self.env.now, ' duracion:', time_to_interruptt, 'al descanso')
                                yield self.env.timeout(time_to_interruptt)
                                print('interrupcion completada en el minuto', self.env.now)
                                self.interrupts += 1
                                #self.state = 'D'
                            time_to_breakk -= self.env.now - start_break
                            time_to_breakk = max(0, time_to_breakk)
                                
                    
            self.completed_tasks +=1
   
            print(f'tarea numero ',self.completed_tasks,' completada', self.env.now)



    
    def take_break(self):
        while True:
            time = self.time_to_break()
            print('solicitando el proximo descanso en ',self.env.now, ' para dentro de ', time)
            yield self.env.timeout(time)
           
            with self.person.request(priority=1) as request:
                yield request
                    
                if self.state == 'W':
                    self.state = 'D'
                    self.process_working.interrupt()
                elif self.state == 'I':
                    print('no puedes descansar por interrupcion', self.env.now)
                

    def interrupting(self):
            while True:
                time = time_to_interrupt()
                print('solicitando proxima interrupcion en ', self.env.now, ' para dentro de :', time)
                yield self.env.timeout(time)
                
                with self.person.request(priority=0) as request:
                    yield request
                    print('se obtuvo la interrupcion (el recurso) en el minuto', self.env.now)
                    if self.state == 'W':
                        self.state = 'I'
                        self.process_working.interrupt()
                    elif self.state == 'D':
                        self.state = 'I'
                        self.process_working.interrupt()
                    else:
                        print(f'no se puede interrumpir en el minuto', self.env.now)
                        continue
                    
                    
            

random.seed(RANDOM_SEED)

#env = simpy.Environment()
#person = Person(env,'S')
#env.run(until=200)
#print(person.breaks)
#print(person.completed_tasks)
#print(person.interrupts)

for i in range(0,1000):
    print(A_break_duration())
