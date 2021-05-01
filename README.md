# 무비 스캐너

CGV 용산 특별 상영관과 메가박스 돌비 상영관의 상영 정보가 추가되면 알려주는 텔레그램 채널들

## 사용법

[무비 스캐너](https://movie-scanner.pages.dev)

## 배포

시간대 설정

```bash
sudo dpkg-reconfigure tzdata
```

패키지 설치

```bash
sudo apt update && sudo apt upgrade -y
```

```bash
sudo apt install python3-pip -y
```

```bash
git clone https://github.com/yehwankim23/movie-scanner.git
```

```bash
pip3 install -r requirements.txt --upgrade
```

Tor 설정 (CGV 용산 스캐너)

```bash
sudo apt install tor -y
```

```bash
tor --hash-password "PASSWORD"
```

```bash
sudo vim /etc/tor/torrc
```

```bash
sudo service tor restart
```

실행

```bash
vim main.py
```

```bash
nohup python3 main.py > output.log &
```
