from functools import wraps

import time
import threading

#import pigpio

def _bezier_softener(p1x: float, p1y: float, p2x: float, p2y: float, steps:int=50, exec_time:float=1 ):

    """
    Bezier Eğrili motor hareket yumuşatma generatörü. Duty cycle verilip istenilen paremeterlere göre adım adım arttırır/azaltır.
    """

    def _bezier(start, stop):
        reverse=False

        diff = stop - start
        if diff < 0:
            reverse=True

        t=1 if reverse else 0

        while t < 1 if not reverse else t > 0:
            # For graphing...
            # x = (3 * t * ( ( 1-t )**2 ) * p1x ) + (3 * (1-t) * (t**2) * p2x) + ( (t**3) * 1 )

            # Gerçek hareket vektör bileşeni
            y = (3 * t * ( ( 1-t )**2 ) * p1y ) + (3 * (1-t) * (t**2) * p2y) + ( (t**3) * 1 )

            t = t + (1/steps) if (not reverse) else t - (1/steps)

            yield int(start + y*diff) if not reverse else int(stop - y*diff)

        yield stop

    return _bezier, steps, exec_time

PWM_FREQ = 20000 # 20kHz
PIGPIO_MAX_DUTY=1000

BEZIER_P1 = (0.6 , 0.00)
BEZIER_P2 = (0.67, 0.61)

class PWMMotorManager:
    def __init__(self, gpio, softener_func=_bezier_softener(BEZIER_P1[0], BEZIER_P1[1], BEZIER_P2[0], BEZIER_P2[1])):
        self.gpio_driver = pigpio.pi()
        self.softener = softener_func[0]
        self.softener_stepping = softener_func[1]
        self.softener_exec_time = softener_func[2]

        self.__duty_prev = 0

        self.__duty = 0

        self.gpio = gpio

        self.gpio_driver.set_mode(self.gpio, pigpio.OUTPUT)
        self.gpio_driver.set_PWM_frequency(self.gpio, PWM_FREQ)
        self.gpio_driver.set_PWM_range(self.gpio, PIGPIO_MAX_DUTY)

        self.__stop_immediate = False
        self.__motor_mutex = threading.Lock()

    def __error_handle(func):
        @wraps(func)
        def tmp(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except:
                self.stop_immediate()
                self.__stop_gpio()
                raise

        return tmp

    def __stop_gpio(self):
        """
        Method to use when something wrong with setting the gpio output happens.
        Kills all outputs.
        """

        pass

    @__error_handle
    def __update_motor_dutycycle(self):
        self.__motor_mutex.acquire()
        if not self.softener is None:
            for duty in self.softener(self.__duty_prev, self.__duty):
                if not self.__stop_immediate:
                    assert self.gpio_driver.set_PWM_dutycycle(self.gpio, duty) == 0
                    self.__duty = duty

                    time.sleep((abs(self.__duty-self.__duty_prev) / PIGPIO_MAX_DUTY ) * self.softener_exec_time / self.softener_stepping )
                else:
                    self.__stop_immediate = False
                    self.__motor_mutex.release()
                    return

        else:
            assert self.gpio_driver.set_PWM_dutycycle(self.gpio, self.__duty) == 0
            self.__motor_mutex.release()

        self.__motor_mutex.release()

    def stop_drive(self):
        self.__duty = 0
        self.__update_motor_dutycycle()

    def stop_immediate(self):
        self.__stop_immediate = True

    @property
    def duty(self):
        return self.__duty

    @duty.setter
    def duty(self, val):
        if isinstance(val, int):
            if val > PIGPIO_MAX_DUTY or val < 0:
                self.stop_immediate()
                raise ValueError('Invalid dutycycle. min 0, max %s' % PIGPIO_MAX_DUTY)

            self.__duty_prev = self.__duty
            self.__duty = val
            self.__update_motor_dutycycle()

        else:
            self.stop_immediate()
            raise ValueError('duty should be an integer.')
