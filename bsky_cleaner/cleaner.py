import time
import random
from datetime import datetime, timedelta
from atproto import Client, models

# Configurações
USERNAME = "seu@handle.bsky.social"
PASSWORD = "sua_senha"
MAX_UNLIKES_PER_HOUR = 200
MAX_DAILY_UNLIKES = 500
SAFE_MODE = True

class BskyLikeCleaner:
    def __init__(self):
        self.client = Client()
        self.total_removals = 0
        self.start_time = time.time()
        self.daily_reset_time = datetime.now() + timedelta(hours=24)

    def _random_wait(self):
        if SAFE_MODE:
            base_wait = 3600 / MAX_UNLIKES_PER_HOUR
            wait_time = random.uniform(base_wait * 0.8, base_wait * 1.2)
            print(f"⏳ Esperando {wait_time:.1f}s...")
            time.sleep(wait_time)
        else:
            time.sleep(3600 / MAX_UNLIKES_PER_HOUR)

    def _check_limits(self):
        if datetime.now() >= self.daily_reset_time:
            print("\n♻️ Resetando contador diário!")
            self.total_removals = 0
            self.daily_reset_time = datetime.now() + timedelta(hours=24)

        if self.total_removals >= MAX_DAILY_UNLIKES:
            print(f"🛑 LIMITE DIÁRIO ATINGIDO: {MAX_DAILY_UNLIKES} likes")
            print("⏳ Reinicie amanhã ou ajuste MAX_DAILY_UNLIKES no código.")
            exit()

        elapsed_seconds = time.time() - self.start_time
        if elapsed_seconds < 3600 and self.total_removals >= MAX_UNLIKES_PER_HOUR * 0.9:
            pause = 3600 - elapsed_seconds
            print(f"🚨 Limite horário próximo! Pausando por {pause/60:.1f} minutos...")
            time.sleep(pause)
            self.start_time = time.time()

    def run(self):
        try:
            self.client.login(USERNAME, PASSWORD)
            print(f"✅ Logado como @{self.client.me.handle}")
            print(f"⚙️ Limite: {MAX_UNLIKES_PER_HOUR}/hora | {MAX_DAILY_UNLIKES}/dia")
            
            cursor = None
            while True:
                self._check_limits()
                
                likes = self.client.com.atproto.repo.list_records(
                    params=models.ComAtprotoRepoListRecords.Params(
                        repo=self.client.me.did,
                        collection='app.bsky.feed.like',
                        limit=100,
                        cursor=cursor
                    )
                )
                
                if not likes.records:
                    print("🌟 Nenhum like restante para remover!")
                    break

                # Ordena do mais antigo (primeiro) ao mais novo (último)
                likes.records.sort(key=lambda x: x.value.created_at)

                for record in likes.records:
                    try:
                        # Formata a data do like (ex: "15/03/2023")
                        like_date = datetime.strptime(
                            record.value.created_at, 
                            '%Y-%m-%dT%H:%M:%S.%fZ'
                        ).strftime('%d/%m/%Y')
                        
                        # Remove o like
                        self.client.com.atproto.repo.delete_record(
                            models.ComAtprotoRepoDeleteRecord.Data(
                                repo=self.client.me.did,
                                collection='app.bsky.feed.like',
                                rkey=record.uri.split('/')[-1]
                            )
                        )
                        self.total_removals += 1
                        print(f"🗓️ {like_date} | ♻️ Removido ({self.total_removals}/{MAX_DAILY_UNLIKES}): {record.uri[:30]}...")
                        self._random_wait()
                        
                    except Exception as e:
                        print(f"⚠️ Erro: {e}")
                        time.sleep(60)
                
                cursor = likes.cursor or None

        except KeyboardInterrupt:
            print("\n🛑 Interrompido pelo usuário")
        finally:
            print(f"\n📊 RESUMO FINAL:")
            print(f"- Likes removidos hoje: {self.total_removals}/{MAX_DAILY_UNLIKES}")
            print(f"- Próximo reset diário: {self.daily_reset_time.strftime('%d/%m às %H:%M')}")

if __name__ == "__main__":
    cleaner = BskyLikeCleaner()
    cleaner.run()