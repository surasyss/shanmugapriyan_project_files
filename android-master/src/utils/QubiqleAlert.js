import { Alert } from 'react-native';

const showAlert = (title, message, positiveButton = null, negativeButton = null) => {
  if (!positiveButton) positiveButton = 'OK';

  const buttons = [
    { text: positiveButton, onPress: () => {} },
  ];
  if (negativeButton) {
    buttons.push({ text: negativeButton, onPress: () => {} });
  }
  Alert.alert(
    title, message, buttons, { cancelable: true },
  );
};

export default showAlert;
