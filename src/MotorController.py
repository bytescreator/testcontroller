import time

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

PWM_FREQ = 10^5 # 100kHz
PIGPIO_MAX_DUTY=100000

BEZIER_P1 = (0.6 , 0.00)
BEZIER_P2 = (0.67, 0.61)

class DriveMotorManager:
    def __init__(self, l_gpio, r_gpio, softener_func=_bezier_softener(BEZIER_P1[0], BEZIER_P1[1], BEZIER_P2[0], BEZIER_P2[1])):
        self.gpio_driver = pigpio.pi()
        self.softener = softener_func[0]
        self.softener_stepping = softener_func[1]
        self.softener_exec_time = softener_func[2]

        self.__left_duty_prev=0

        self.__left_duty = 0
        self.__right_duty = 0

        self.left_gpio = l_gpio
        self.right_gpio = r_gpio

    def __update_motor_dutycycle(self):
        if not self.softener is None:
            softeners=zip(
                self.softener(self.__left_duty_prev, self.__left_duty),
                self.softener(self.__right_duty_prev, self.__right_duty)
            )

            for duty_l, duty_r in softeners:
                assert self.gpio_driver.hardware_PWM(self.left_gpio, PWM_FREQ, duty_l) == 0
                assert self.gpio_driver.hardware_PWM(self.right_gpio, PWM_FREQ, duty_r) == 0
                time.sleep(( abs( self.__left_duty-self.__left_duty_prev + self.__right_duty-self.__right_duty_prev ) / 2 
                    / PIGPIO_MAX_DUTY ) * self.softener_exec_time / self.softener_stepping )

        else:
            assert self.gpio_driver.hardware_PWM(self.left_gpio, PWM_FREQ, self.__left_duty) == 0
            assert self.gpio_driver.hardware_PWM(self.right_gpio, PWM_FREQ, self.__right_duty) == 0

    def stop_drive(self):
        self.__left_duty = 0
        self.__right_duty = 0
        self.__update_motor_dutycycle()

    @property
    def left_duty(self):
        return self.__left_duty

    @left_duty.setter
    def left_duty(self, val):
        if isinstance(val, int):
            self.__left_duty = val
            self.__update_motor_dutycycle()
        else:
            raise ValueError('left_power should be an integer.')
    
    @property
    def right_duty(self):
        return self.__right_duty

    @right_duty.setter
    def right_duty(self, val):
        if isinstance(val, int):
            self.__left_duty = val
            self.__update_motor_dutycycle()
        else:
            raise ValueError('left_power should be an integer.')
    