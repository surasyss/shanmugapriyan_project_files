import React from 'react';
import { FlatList } from 'react-native';
import InvoiceEmpty from '../InvoiceEmpty';
import InvoiceImage from '../InvoiceImage';

export default function InvoiceImages(props) {
  let { images } = props;
  const { onPress } = props;
  if (!images) images = [];

  return (
    <FlatList
      data={images}
      renderItem={({ item, index }) => (
        <InvoiceImage
          image={item}
          index={index}
          count={images.length}
          onPress={onPress}
        />
      )}
      ListEmptyComponent={(
        <InvoiceEmpty
          message="There are no images to display"
        />
            )}
      numColumns={2}
      keyExtractor={(item) => item.thumbnail}
      listKey={(item, index) => index.toString()}
    />
  );
}
