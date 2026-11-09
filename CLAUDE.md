# כללי עבודה – intro_to_gcp

## הקשר
- שירות Cloud Run בשם `message-page` (אזור me-west1, פרויקט `ai-gcp-course-test`) שקורא את `message.txt` מ-bucket פרטי `ai-gcp-course-test-messages`.
- השירות רץ בזהות `message-reader`, שיש לה רק `roles/storage.objectViewer` על ה-bucket הזה.
- שמות ה-bucket והקובץ מועברים במשתני סביבה `BUCKET_NAME` / `OBJECT_NAME`, לא בקוד.

## כללי שיפור מתמיד
- **גישה ציבורית מחייבת אישור מפורש.** לפני פריסה עם `--allow-unauthenticated` שואלים את המשתמש אם השירות יהיה ציבורי או רק למחוברים, ולא מניחים ברירת מחדל.
  *מקור: הפריסה הראשונה נחסמה כי ההחלטה על גישה ציבורית לא אושרה מראש.*
- **בודקים את החיבור בפועל, לא רק שהפריסה הצליחה.** אחרי כל פריסה או שינוי הרשאות:
  1. הדף מחזיר 200 ומציג את תוכן הקובץ.
  2. קריאה אנונימית ישירה ל-`https://storage.googleapis.com/<bucket>/message.txt` מחזירה 403 (ה-bucket פרטי).
  3. החלפת הקובץ מופיעה ברענון, ושם ה-revision (`gcloud run services describe ... --format="value(status.latestReadyRevisionName)"`) לא משתנה.
  4. שינוי זמני של שם הקובץ מחזיר דף "הקובץ לא נמצא" עם סטטוס 404 – ואז מחזירים את השם.
- **קבצי טקסט מ-Windows:** כותבים UTF-8 ללא BOM; הקוד מקודד עם `utf-8-sig` כדי לא להציג תו נסתר אם BOM בכל זאת הגיע.
