import 'package:flutter/material.dart';

Image logoWidget(String imageName) {
  //brain logo
  return Image.asset(
    imageName,
    fit: BoxFit.fitWidth,
    width: 240,
    height: 240,
  );
}

TextField reusableTextField(
    String text,
    IconData icon,
    bool isPasswordType, //textfield for login pages
    TextEditingController controller,
    {TextInputAction textInputAction = TextInputAction.next,
    Function(String)? onSubmitted,
    Key? givenKey}) {
  return TextField(
    controller: controller,
    obscureText: isPasswordType,
    enableSuggestions: !isPasswordType,
    autocorrect: !isPasswordType,
    cursorColor: Colors.white,
    textInputAction: textInputAction,
    onSubmitted: onSubmitted,
    style: const TextStyle(color: Colors.white),
    decoration: InputDecoration(
      prefixIcon: Icon(icon, color: Colors.white70),
      labelText: text,
      labelStyle: const TextStyle(color: Colors.white70),
      filled: true,
      floatingLabelBehavior: FloatingLabelBehavior.never,
      fillColor: Colors.white.withValues(alpha: 0.3),
      border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(30.0),
          borderSide: const BorderSide(width: 0, style: BorderStyle.none)),
    ),
    keyboardType: isPasswordType
        ? TextInputType.visiblePassword
        : TextInputType.emailAddress,
    key: givenKey,
  );
}

Container firebaseUIButton(BuildContext context, String title, Function onTap,
    {Key? givenKey}) {
  return Container(
    width: MediaQuery.of(context).size.width,
    height: 50,
    margin: const EdgeInsets.fromLTRB(0, 10, 0, 20),
    decoration: BoxDecoration(borderRadius: BorderRadius.circular(90)),
    key: givenKey,
    child: ElevatedButton(
      onPressed: () {
        onTap();
      },
      style: ButtonStyle(
          backgroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.pressed)) {
              return Colors.black26;
            }
            return Colors.white;
          }),
          shape: WidgetStateProperty.all<RoundedRectangleBorder>(
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)))),
      child: Text(
        title,
        style: const TextStyle(
            color: Colors.black87, fontWeight: FontWeight.bold, fontSize: 16),
      ),
    ),
  );
}

//pop up for training instructions
MaterialButton instructionsPopUp ({
  required BuildContext context,
  String title = 'Instructions',
  required Widget content,
}) {
  return MaterialButton(
    onPressed: () {
      showDialog(
        context: context,
        builder: (BuildContext context) => InstructionsDialog(
          title: title,
          content: content,
        ),
      );
    },
    child: Text('Show Instructions'),
  );
}

class InstructionsDialog extends StatelessWidget {
  //class to add custom training dialog
  final String title;
  final Widget content;
  final List<Widget>? actions;

  const InstructionsDialog({
    super.key,
    this.title = 'Instructions',
    required this.content,
    this.actions,
  });

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      title: Text(title),
      content: SingleChildScrollView(
        child: content,
      ),
      actions: actions ??
          [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: Text('Close'),
            ),
          ],
    );
  }
}
