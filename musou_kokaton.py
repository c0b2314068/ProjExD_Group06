import math
import os
import random
import sys
import time
import pygame as pg

WIDTH, HEIGHT = 1000, 600  # ゲームウィンドウの幅，高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def check_bound(obj_rct:pg.Rect) -> tuple[bool, bool]:
    """
    Rectの画面内外判定用の関数
    引数：こうかとんRect，または，爆弾Rect，またはビームRect
    戻り値：横方向判定結果，縦方向判定結果（True：画面内／False：画面外）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:  # 横方向のはみ出し判定
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:  # 縦方向のはみ出し判定
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 1.0),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 1.0),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 1.0),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 1.0),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 1.0),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 1.0),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"
        self.hyper_life = 0
        self.life = 3  # こうかとんの初期体力

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        if self.state == "hyper":   # 無敵状態のとき
            self.image = pg.transform.laplacian(self.image)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface, score):
        """
        押下キーに応じてこうかとんを移動させる
        スコアが100より大きいとき，右Shift押下で500フレームの間こうかとんが無敵状態になる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        引数3 score:Scoreオブジェクト
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.sum_mv = sum_mv
        key_lst = pg.key.get_pressed()
              
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if key_lst[pg.K_LSHIFT]:   #左シフトキーが押されたら
            self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])  #コウカトンの速度を2倍    
            if check_bound(self.rect) != (True, True):
                self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])

        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        if key_lst[pg.K_RSHIFT] and score.value >= 100:
            score.value -= 100  # スコアを100消費
            self.state = "hyper"
            self.hyper_life = 500  # 発動時間
        if self.state == "hyper":   # 無敵状態のとき
            self.image = pg.transform.laplacian(self.image)
            self.hyper_life -= 1
            if self.hyper_life < 0:  # 無敵状態が終わったら
                self.state = "normal"
                self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird, score):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height/2

        # self.bosvx, self.bosvy = calc_orientation(bos.rect, bird.rect)  
        # self.rect.centerx = bos.rect.centerx
        # self.rect.centery = bos.rect.centery+bos.rect.height/2

        self.speed = 6
        self.state="active"
        if score.value >= 100:  # 得点に応じてスピードを変更
            self.speed = 7 
        if score.value >= 200:
            self.speed = 8
        if score.value >= 300:
            self.speed = 9 

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        yoko, tate = check_bound(self.rect)  
        if not yoko:
            self.vx *= -1   # 爆弾を反射させる
        if not tate:
            self.vy *= -1
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)

        # self.rect.move_ip(self.speed*self.bosvx, self.speed*self.bosvy)
        #if check_bound(self.rect) != (True, True):
            # self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird, angle0 : float = 0, a=2.0):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        self.angle = angle0 + math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), self.angle, a)
        self.vx = math.cos(math.radians(self.angle))
        self.vy = -math.sin(math.radians(self.angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10
        self.time = 0

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        if self.time > 0:
                print(self.time)
                
                self.time -= 1
                self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), self.angle, 6.0)
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class NeoBeam:
    """
    ビームの同時発射に関するクラス
    """
    def __init__(self, bird : Bird, num : int):
        self.bird = bird
        self.num = num
    
    def gen_beams(self):
        beams = []
        for angle in range(-50, +51, 100//(self.num-1)):
            beam = Beam(self.bird, angle)
            beams.append(beam)
        return beams


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = random.choice(__class__.imgs)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vy = +6
        self.bound = random.randint(50, HEIGHT/2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 200)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.centery += self.vy


class Gravity(pg.sprite.Sprite):
    def __init__(self, life : int):
        super().__init__()
        self.life = life
        self.image = pg.Surface((WIDTH, HEIGHT))
        color = (0, 0, 0)
        pg.draw.rect(self.image, color, (0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(128)
        self.rect = self.image.get_rect()
    
    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.kill()


class Shield(pg.sprite.Sprite):
    """
    防御壁に関するクラス    
    """
    def __init__(self, bird : Bird, life : int):
        super().__init__()
        self.life = life
        x, y = 20, bird.rect.height*2
        self.image = pg.Surface((x, y))
        color = (0, 0, 255)
        pg.draw.rect(self.image, color, (0, 0, x, y))
        self.vx, self.vy = bird.dire
        self.angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(self.image, self.angle, 1.0)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*bird.dire[1]
        self.rect.centerx = bird.rect.centerx+bird.rect.width*bird.dire[0]

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()


class Score:
    """
    打ち落とした爆弾，敵機の数のスコアとこうかとんの体力を表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self, text: str, color: tuple, xy: tuple):
        self.text = text
        self.font = pg.font.Font(None, 50)

        #self.boss=0

        self.color = color
        self.value = 0
        self.image = self.font.render(f"{self.text}: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.left = xy[0]
        self.rect.y = xy[1]

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"{self.text}: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class EMP():  # empに関するクラス
    def __init__(self,emys: pg.sprite.Group ,bombs: pg.sprite.Group, screen : pg.Surface):
        for emy in emys:
            emy.interval = math.inf
            emy.image=pg.transform.laplacian(emy.image)
            emy.image.set_colorkey((0,0,0))
        for bomb in bombs:
            bomb.speed/=2
            bomb.state="inactive"



#itemに関するクラス
class Spanner(pg.sprite.Sprite):
    

    def __init__(self, obj: "Enemy"):
        """
        アイテムを生成する
        引数1 obj：爆発する敵機インスタンス
        """
        super().__init__()
        img = pg.image.load(f"fig/spanner.png")
        self.image = pg.transform.scale(img, (img.get_width() * 0.1, img.get_height() * 0.1)) #画像を縮小
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.speed = 3
        self.time = 500


    def update(self):
        self.rect.y += self.speed #下方向に落下
    

class Doublescore(pg.sprite.Sprite):
    def __init__(self, obj: "Enemy"):
        """
        アイテムを生成する
        引数1 obj：爆発する敵機インスタンス
        """
        super().__init__()
        img = pg.image.load(f"fig/double.png")
        self.image = pg.transform.scale(img, (img.get_width() * 0.03, img.get_height() * 0.03)) #画像を縮小
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.speed = 3

    def update(self):
        self.rect.y += self.speed #下方向に落下


class BOSS(pg.sprite.Sprite):
    """
    ボスに関するクラス
    """    
    image = pg.transform.scale2x(pg.image.load("fig/alien1.png"))

    def __init__(self):
        super().__init__()
        self.rect = self.image.get_rect()
        self.rect.center = WIDTH/2, -100
        self.vy = +6
        self.life=20
        self.bound = HEIGHT/5  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(10, 80)  # 爆弾投下インターバル

    def update(self):
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.centery += self.vy

        
class Color():
    def __init__(self):
        self.image=pg.Surface((1000, 600))
        pg.draw.rect(self.image,(255, 255, 255),(0, 0), )


class Enemy2(pg.sprite.Sprite):
    """
    敵2に関するクラス
    """
    def __init__(self):
        super().__init__()
        self.tmr = 0  #タイマー
        self.life = 30  #HP
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/alien1.png"), 0, 1.5)
        self.rect = self.image.get_rect()
        self.rect.center = (WIDTH/2, 0)
        self.vx = random.randint(2, 4)
        self.vy = +1  #降下速度
        self.bound_x = WIDTH//12  #横に動ける範囲
        self.bound_y = HEIGHT//6  #縦に動ける範囲
        self.state = "down"
    
    def update(self, bullets : pg.sprite.Group, bird : Bird):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        停止位置_bound_yまで降下したら，_stateを活動状態に変更する
        引数1 bullets : 弾のGroupオブジェクト
        引数2 bird : こうかとんクラス
        """
        #一定間隔で攻撃を行う
        if self.tmr % 500 == 100 :
            self.n_way(12, random.randint(4, 7), bullets, bird)
        if self.tmr % 50 == 25:
            self.n_way(1, 6.0, bullets, bird)
        if self.tmr % 150 == 35:
            self.predict(16, bullets, bird)
        if self.tmr % 15 == 14:
            bullets.add(Bullet(5, random.randint(0, 359), self))
        
        #降下しきるまで活動しない
        if self.state != "down":
            self.tmr += 1
        if self.rect.centery > self.bound_y:
            self.vy = 0
            self.state = "move"
        
        #左右に動かす処理
        if self.state == "move":
            self.rect.move_ip(self.vx, 0)
        if self.rect.left < self.bound_x or WIDTH-self.bound_x < self.rect.right:
            self.vx *= -1
            self.rect.move_ip(self.vx, 0)
        self.rect.centery += self.vy

    def PlusMin(self, a, b):
        """
        0以上であるもののうち最も小さい数を返す関数
        """
        if a < 0 and b < 0:
            return 0
        if a < 0:
            return b
        if b < 0:
            return a
        if a < b:
            return a
        else:
            return b
        
    def n_way(self, n : int, speed : float, bullets : pg.sprite.Group, bird : Bird):
        """
        n個の弾を円状に発射する
        引数1 n : 弾の個数
        引数2 speed : 弾の速さ
        引数3 bullets : 弾のGroupオブジェクト
        引数4 bird : こうかとんクラス
        """
        #自分から見たこうかとんの角度を計算
        x, y = calc_orientation(self.rect, bird.rect)
        angle0 = int(math.degrees(math.atan2(y, x)))

        #角度の差が等しいn個のBulletオブジェクトを生成する
        for angle in range(0+angle0, 360+angle0, 360//n):
            bullets.add(Bullet(speed, angle, self))
    
    def predict(self, speed : float, bullets : pg.sprite.Group, bird : Bird):
        """
        こうかとんの動きを予測して弾を発射する
        引数1 speed : 弾の速さ
        引数2 bullets : 弾のGroupオブジェクト
        引数3 bird : こうかとんクラス
        """
        pred_x, pred_y = 0, 0  #予測位置の初期化
        bspeed_x = bird.speed*bird.sum_mv[0]  #こうかとんの速度のx成分
        bspeed_y = bird.speed*bird.sum_mv[1]  #こうかとんの速度のy成分
        pos_x = self.rect.centerx - bird.rect.centerx 
        pos_y = self.rect.centery - bird.rect.centery
        l = math.sqrt(pos_x**2 + pos_y**2)
        v = math.sqrt(bspeed_x**2 + bspeed_y**2)
        t1, t2 = 0, 0
        ang1 = abs(math.degrees(math.atan2(bird.sum_mv[1], bird.sum_mv[0])))
        ang2 = abs(math.degrees(math.atan2(pos_y, pos_x)))
        if abs(ang1 - ang2) > 180:
            ang = 360 - abs(ang1 - ang2)
        else:
            ang = abs(ang1 - ang2)
        
        t1 = l / (-speed*math.sqrt(1 - ((v/speed)*math.sin(ang))**2) - v*math.cos(ang))
        t2 = l / (speed*math.sqrt(1 - ((v/speed)*math.sin(ang))**2) - v*math.cos(ang))
        t = self.PlusMin(t1, t2)
        
        pred_x = bird.rect.centerx + bspeed_x*t
        pred_y = bird.rect.centery + bspeed_y*t

        x_diff, y_diff = (pred_x-self.rect.centerx), (pred_y-self.rect.centery)
        norm = math.sqrt(x_diff**2+y_diff**2)
        angle = int(math.degrees(math.atan2(y_diff/norm, x_diff/norm)))
        bullets.add(Bullet(speed, angle, self))


class Bullet(pg.sprite.Sprite):
    """
    弾に関するクラス
    """
    def __init__(self, speed : float, angle : float, emy2 : Enemy2):
        """
        引数1 speed : 弾の速度
        引数2 angle : 弾の角度(度数法)
        引数3 emy2 : 弾を発射する敵のクラス
        """
        super().__init__()
        rad = 10
        self.image = pg.Surface((2*rad, 2*rad))
        color = (random.randint(50, 100), random.randint(100, 150), random.randint(50, 100))
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        self.rect.centerx = emy2.rect.centerx
        self.rect.centery = emy2.rect.centery
        self.speed = speed  #弾の速度
        self.vx = math.cos(math.radians(angle))  #速度のx成分
        self.vy = math.sin(math.radians(angle))  #速度のy成分

    def update(self):
        """
        弾を速度ベクトルself.vx, self.vyに基づき移動させる
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score("Score", (0, 0, 255), (0, HEIGHT-50))

    #こうかとんと敵に関するグループ/スプライト
    bird = Bird(3, (900, 400))
    life = Score("Life", (255, 0, 0), (0, HEIGHT-100))  # こうかとんの体力表示オブジェクト
    life.value = bird.life
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    emy2s = pg.sprite.Group()
    bullets = pg.sprite.Group()
    gravitys = pg.sprite.Group()
    shields = pg.sprite.Group()
    boss = pg.sprite.Group()

    #アイテムのグループ
    spanners = pg.sprite.Group()
    doublescores = pg.sprite.Group()
    btime = 0

    tmr = 0
    rand = 0
    clock = pg.time.Clock()
    
    while True:

        #こうかとんの操作に関する処理
        key_lst = pg.key.get_pressed()
        mode = 0
        if key_lst[pg.K_LSHIFT]:
            mode = 1
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            #ビーム
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                if not mode:
                    if btime > 0: 
                        beams.add(Beam(bird,a=6))
                        btime -= 1
                    else:
                        beams.add(Beam(bird))
                else:
                    neobeam = NeoBeam(bird, 7)
                    for beam in neobeam.gen_beams():
                        beams.add(beam)
            #EMP
            if event.type == pg.KEYDOWN and event.key == pg.K_e:
                if score.value > 20:
                    EMP(emys, bombs, screen)
                    score.value-=20
            #重力場
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                if score.value >= 200:
                    score.value -= 200
                    gravitys.add(Gravity(400))
            #防御壁
            if event.type == pg.KEYDOWN and event.key == pg.K_v:
                if score.value >= 50 and len(shields) == 0:
                    score.value -= 50
                    shields.add(Shield(bird, 400))
        screen.blit(bg_img, [0, 0])

        #敵の出現処理
        if tmr%1300 == 9: # 1300フレームに1回，強めの敵を出現させる
            emy2s.add(Enemy2())
        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())
        if tmr% 1000 == 500:
            boss.add(BOSS())

        #爆弾の生成
        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird, score))
        for bos in boss:
            if bos.state == "stop" and tmr%bos.interval == 0:
                bombs.add(Bomb(bos, bird, score))

        #ビームと通常敵に関する処理
        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト
            rand = random.randint(1,8)  #4分の1の確率でアイテム生成
            if rand == 1:
                spanners.add(Spanner(emy))
            elif rand == 2:
                doublescores.add(Doublescore(emy))

        #アイテムの取得に関する処理
        for spanner in pg.sprite.spritecollide(bird, spanners, True):
            btime = 10
            bird.change_img(6.1, screen)  # こうかとん覚醒エフェクト
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:    
                neobeam = NeoBeam(bird, 7)
                for beam in neobeam.gen_beams():
                    beams.add(beam)
        for doublescore in pg.sprite.spritecollide(bird, doublescores, True):
            bird.change_img(6, screen)   # こうかとん喜びエフェクト
            score.value *= 2  # 2倍点アップ          
        
        #ビームと敵の接触の処理
        for bos in pg.sprite.groupcollide(boss, beams, False, True):
            bos.life -= 1
            score.value += 5
            if bos.life < 0:
                bos.kill()
                exps.add(Explosion(bos, 200))
                score.value += 200
        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ
        for emy2 in pg.sprite.groupcollide(emy2s, beams, False, True):
            emy2.life -= 1
            score.value += 5
            if emy2.life < 0:
                emy2.kill()
                exps.add(Explosion(emy2, 200))
                score.value += 200
        
        #重力場に関する処理
        for emy in pg.sprite.groupcollide(emys, gravitys, True, False).keys():
            exps.add(Explosion(emy, 50))
            score.value += 10
        for bomb in pg.sprite.groupcollide(bombs, gravitys, True, False).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1
        for bullet in pg.sprite.groupcollide(bullets, gravitys, True, False):
            pass
        
        #防御壁に関する処理
        for bomb in pg.sprite.groupcollide(bombs, shields, True, False).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1
        for bullet in pg.sprite.groupcollide(bullets, shields, True, False):
            pass
        
        #こうかとんと爆弾についての処理
        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            if bomb.state == "inactive":
                continue
            if bird.state == "hyper":  # こうかとんが無敵状態のとき
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                score.value += 1
            elif bird.state == "normal":  # こうかとんが通常状態のとき
                bird.life -= 1  # 体力を1減らす
                life.value = bird.life # 体力の更新
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                red = pg.Surface((WIDTH, HEIGHT))
                pg.draw.rect(red, (255, 0, 0), (0, 0, WIDTH, HEIGHT))
                red.set_alpha(64)
                screen.blit(red,(0,0))
                pg.display.update()
            if bird.life <= 0:  # こうかとんの体力が0以下になったとき
                bird.change_img(8, screen) # こうかとん悲しみエフェクト
                score.update(screen)
                life.update(screen)
                pg.display.update()
                time.sleep(2)
                return
        
        #こうかとんと弾に関する処理
        for bullet in pg.sprite.spritecollide(bird, bullets, True):
            if bird.state == "hyper":  # こうかとんが無敵状態のとき
                pass
            elif bird.state == "normal":  # こうかとんが通常状態のとき
                bird.life -= 1  # 体力を1減らす
                life.value = bird.life # 体力の更新
                red = pg.Surface((WIDTH, HEIGHT))
                pg.draw.rect(red, (255, 0, 0), (0, 0, WIDTH, HEIGHT))
                red.set_alpha(64)
                screen.blit(red,(0,0))
                pg.display.update()
            if bird.life <= 0:  # こうかとんの体力が0以下になったとき
                bird.change_img(8, screen) # こうかとん悲しみエフェクト
                score.update(screen)
                life.update(screen)
                pg.display.update()
                time.sleep(2)
                return
        
        bird.update(key_lst, screen, score)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        boss.update()
        boss.draw(screen)
        emy2s.update(bullets, bird)
        emy2s.draw(screen)
        bullets.update()
        bullets.draw(screen)
        bombs.update()
        bombs.draw(screen)
        shields.update()
        shields.draw(screen)
        exps.update()
        exps.draw(screen)
        gravitys.update()
        gravitys.draw(screen)
        score.update(screen)
        spanners.update()
        spanners.draw(screen)
        doublescores.update()
        doublescores.draw(screen)
        life.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    print()
    pg.quit()
    sys.exit()