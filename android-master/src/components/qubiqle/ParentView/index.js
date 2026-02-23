import React from 'react';
import { ActivityIndicator, View } from 'react-native';
import styles from './styles';
import Colors from '../../../styles/Colors';

export default function ParentView(props) {
  const { loading, children, hoverLoading } = props;
  const isVisibleLoading = loading || hoverLoading;
  return (
    <>
      {isVisibleLoading
        ? (
          <View style={styles.loading}>
            <ActivityIndicator size="large" color={Colors.primary} />
          </View>
        ) : null}
      {loading ? null : children}
    </>
  );
}
