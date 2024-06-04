import random
import simpy

RANDOM_SEED = 42
TASK_MEAN = 20.0
TASK_SIGMA = 2.0

INTERRUPTION_MEAN = 10.0
INTERRUPTION_SIGMA = 3.0

BREAK_MEAN = 60.0
BREAK_SIGMA = 3.0

def working_duration():
    t = random.normalvariate(TASK_MEAN, TASK_SIGMA)

    while t <= 0:
        t = random.normalvariate(TASK_MEAN, TASK_SIGMA)
    return t

def time_to_interrupt():
    t = random.normalvariate(INTERRUPTION_MEAN, INTERRUPTION_SIGMA)

    while t <= 0:
        t = random.normalvariate(INTERRUPTION_MEAN, INTERRUPTION_SIGMA)
    return t

def time_to_break():
    t = random.normalvariate(BREAK_MEAN, BREAK_SIGMA)

    while t <= 0:
        t = random.normalvariate(BREAK_MEAN, BREAK_SIGMA)
    return t

def break_duration():
        time = random.normalvariate(BREAK_MEAN, BREAK_SIGMA)

        while time <= 0:
            time = random.normalvariate(BREAK_MEAN, BREAK_SIGMA)
        return time



class Person:
    def __init__(self,env,state):
        self.state = state
        self.env = env
        self.person = simpy.PreemptiveResource(env,capacity=1)
        self.completed_tasks = 0
        self.breaks = 0
        self.interrupts = 0

        self.process_working = env.process(self.working())
        env.process(self.interrupting())
        self.process_break = env.process(self.take_break())

    def working(self):
        while True:
            working_time = working_duration()
            while working_time:
                with self.person.request(priority=2) as request:
                    print(f'solicitando trabajar unos ', working_time, ' minutos')
                    yield request
                    start = self.env.now
                    try:
                        self.state = 'W'
                        print('trabajando')
                        yield self.env.timeout(working_time)
                        working_time = 0
                    except simpy.Interrupt:
                        working_time -= self.env.now - start
                        print(f'trabajo interrumpido en el minuto ',self.env.now,', queda por completar unos ', working_time, ' minutos')
            self.completed_tasks +=1
            print(f'tarea numero ',self.completed_tasks,' completada')

    
    def take_break(self):
        while True:
            time_break = break_duration()
            #print('solicitando descanso')
            with self.person.request(priority=1) as request:
                while time_break and self.state =='W':
                    yield request
                    try:
                        print(f'interrumpiendo trabajo para descansar en el minuto',self.env.now)
                        self.process_working.interrupt()
                        self.state = 'D'
                        print(f'descansando unos ',time_break, ' minutos')
                        yield self.env.timeout(time_break)
                        print(f'descanso completado')
                    except simpy.Interrupt:
                        self.state = 'I'
                        interrupt_start = self.env.now
                        print('descanso interrumpido')
                        with self.person.request(priority=1) as request:
                            yield request
                            print('retomando descanso')
                            yield self.env.timeout(max(0,time_break - (self.env.now - interrupt_start)))
                            time_break = 0
            self.breaks += 1
            print(f'descanso numero ',self.breaks, ' completado')
                        
        """   
            if self.state == 'W':
                print(f'interrumpiendo trabajo para descansar en el minuto',self.env.now)
                self.process_working.interrupt()
                time_break = time_to_break()
                start_break = self.env.now

                while time_break :
                    start = self.env.now
                    try:
                        yield self.env.timeout(time_break)
                        print(f'descansando unos ',time_break, ' minutos')
                        time_break = 0
                    except simpy.Interrupt:
                        self.state = 'I'
                        interrupt_time = self.env.now - start
                        if interrupt_time >= (start_break + time_break - self.env.now):
                            print('la interrupcion duro mas que lo que restaba de descanso')
                            time_break = 0
                        else:
                            time_break -= interrupt_time
                            print(f'queda por descansar unos ',time_break, ' minutos')


                        with self.person.request(priority=1) as request:
                            print('solicitando retomar el descanso')
                            yield request
                            print('retomando descanso')
                            yield self.env.timeout(5)
                        self.state = 'D'
                self.breaks += 1
                print(f'descanso numero ',self.breaks, ' completado')
    """
            
    
                      
    def interrupting(self):
        while True:
            #print('solicitando proxima interrupcion')
            time = time_to_interrupt()
            yield self.env.timeout(time)
            if self.state == 'W':
                print(f'interrumpiendo trabajo en el minuto ', self.env.now)
                self.process_working.interrupt()
            if self.state == 'D':
                print(f'interrumpiendo descanso en el minuto', self.env.now)
                self.process_break.interrupt()
            if self.state == 'W' or self.state == 'D':
                print('interrumpiendo')
                self.interrupts += 1
                print(f'interrupcion',self.interrupts,' completada')
                yield self.env.timeout(time_to_interrupt())

random.seed(RANDOM_SEED)

env = simpy.Environment()
person = Person(env,'S')
env.run(until=1000)