# **Convert To Solid**

This command converts the specified sheet metal body to a solid body.

<u>The documentation is only available in English and Japanese, but the display switches with each Fusion360 language setting.
If the display is inappropriate, please contact us and we will correct it.</u>

---

## **Usage** :

After activation of the add-in, the "Convert to Solid" command will be added within "Sheet Metal" - "Modify".

![Alt text](./resources_readme/menu_eng.png)

By clicking on it, a dialog box appears.

![Alt text](./resources_readme/dialog_eng.png)

Select the sheet metal body to be converted and press the OK button.

---

## **Deliverables** :

The actual process is not a conversion, but the following process.
+ Create a sketch on the flat surface of the sheet metal body.
+ Create solid body with rotate command.
+ Combine to create a solid body.
+ Delete unnecessary bodies.

These processes are made into a timeline group.

![Alt text](./resources_readme/result.png)

※Because a group cannot be created within a timeline group, a group will not be created if it is within a group.

---

## **Note** :

+ None in particular.

---

## **Action** :

The following environment is confirmed.

- Fusion360 Ver2.0.15509
- Windows 10 64bit Pro , Home

---
---

# *** 以下は日本語です。***

# **ソリッドへ変換**
本コマンドは、指定したシートメタルボディをソリッドボディに変換します。

---

## **使用法** :

アドイン起動後は、"シートメタル" - "修正"  内に "ソリッドへ変換" コマンドが追加されます。

![Alt text](./resources_readme/menu_jpn.png)

クリックする事でダイアログが表示されます。

![Alt text](./resources_readme/dialog_jpn.png)

変換するシートメタルボディを選択し、OKボタンを押してください。
+ 外部コンポーネントのシートメタルボディは対象外です。

---

## **成果物** :

実際の処理は変換では無く、以下の処理を行っています。
+ シートメタルボディの平らな面にスケッチを作成。
+ 回転コマンドでソリッドボディを作成。
+ 結合してソリッドボディ化。
+ 不要なボディの削除。

これらの処理をタイムライングループにしています。

![Alt text](./resources_readme/result.png)

※タイムライングループ内にグループを作成出来ない為、グループ内の場合はグループを作成しません。

---

## **注意** :

+ 特にありません。

---

## **アクション** :

以下の環境で確認しています。

- Fusion360 Ver2.0.15509
- Windows10 64bit Pro , Home

---