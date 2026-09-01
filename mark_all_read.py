from gmail_auth import get_gmail_service
import time

def mark_all_as_read():
    service = get_gmail_service()
    print("📡 Start: alle ongelezen e-mails markeren als gelezen...")
    
    total_marked = 0
    while True:
        # Haal maximaal 500 ongelezen e-mails per keer op
        results = service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=500
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            print(f"✅ Klaar! {total_marked} e-mails gemarkeerd als gelezen.")
            break
        
        msg_ids = [msg['id'] for msg in messages]
        
        # Markeer ze allemaal als gelezen in één batch
        for msg_id in msg_ids:
            try:
                service.users().messages().modify(
                    userId='me',
                    id=msg_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                total_marked += 1
                print(f"📧 {total_marked} - Gemarkeerd: {msg_id}")
            except Exception as e:
                print(f"⚠️ Fout bij {msg_id}: {e}")
        
        print(f"⏳ {len(msg_ids)} e-mails verwerkt, nog bezig...")
        time.sleep(0.5)  # Even pauze om rate-limiting te voorkomen

if __name__ == "__main__":
    mark_all_as_read()