import React from 'react';
import {
  Image, TextInput, TouchableOpacity, View
} from 'react-native';
import styles from './styles';
import Images from '../../../styles/Images';

export default function SearchBar(props) {
  const {
    onSubmit, style, onSearchCancel, searchText, onTextChange, placeholder
  } = props;

  return (
    <View style={[styles.container, style]}>
      <View style={styles.searchSection}>
        <Image
          style={styles.searchIcon}
          source={Images.search}
          resizeMode="contain"
        />
        <TextInput
          style={styles.input}
          placeholder={placeholder}
          onChangeText={(text) => {
            onTextChange(text);
          }}
          underlineColorAndroid="transparent"
          value={searchText}
          onSubmitEditing={onSubmit}
          returnKeyType="search"
          autoFocus
        />

        <TouchableOpacity onPress={onSearchCancel}>
          <Image
            source={Images.close}
            style={styles.cancelIcon}
            resizeMode="contain"
          />
        </TouchableOpacity>
      </View>

    </View>
  );
}
