import React from 'react';
import {
  Image, Text, TouchableOpacity, View
} from 'react-native';
import styles from './styles';

export default function InvoiceImage(props) {
  const {
    image, index, count, onPress
  } = props;
  const numberViews = [styles.oddView, styles.evenView];
  const { thumbnail } = image;

  return (
    <TouchableOpacity
      style={[styles.mainView, numberViews[index % 2]]}
      onPress={() => onPress(image, index, count)}
    >
      <Image
        source={{ uri: thumbnail }}
        style={styles.image}
        resizeMode="contain"
      />

      <View style={styles.waterMarkView}>
        <Text style={styles.waterMark}>
          {index + 1}
          /
          {count}
        </Text>
      </View>

    </TouchableOpacity>
  );
}
